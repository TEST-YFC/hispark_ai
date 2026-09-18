"""Fail-fast structural checks for generated Micro FP32 training artifacts."""
from __future__ import annotations
import re
import hashlib
from pathlib import Path


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _text(path):
    _require(Path(path).is_file(), f"missing training graph evidence: {path}")
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _nodes(dot):
    result = {}
    for match in re.finditer(r"(?m)^\s*([A-Za-z][A-Za-z0-9_]*)\s*\[([^\n]*?)\];", dot):
        attrs = match.group(2)
        label = re.search(r'label="((?:\\.|[^"\\])*)"', attrs)
        result[match.group(1)] = label.group(1) if label else attrs
    return result


def _edges(dot):
    return re.findall(r"(?m)^\s*([A-Za-z][A-Za-z0-9_]*)\s*->\s*([A-Za-z][A-Za-z0-9_]*)", dot)


def _label_lines(label):
    return [line.strip() for line in label.replace("\\n", "\n").split("\n") if line.strip()]


def _find_label(nodes, name, primitive=None, required_text=None):
    _require(isinstance(name, str) and name, "node name is required")
    hits = []
    for node, label in nodes.items():
        lines = _label_lines(label)
        if name not in lines:
            continue
        if primitive is not None and f"prim={primitive}" not in lines:
            continue
        if required_text is not None and required_text not in lines:
            continue
        hits.append((node, label))
    _require(len(hits) == 1,
             f"expected exactly one node name={name!r} primitive={primitive!r} role={required_text!r}, got {len(hits)}")
    return hits[0]


def _reachable(edges, start, wanted, blocked=None):
    blocked = set(blocked or ())
    adjacency = {}
    for left, right in edges:
        adjacency.setdefault(left, set()).add(right)
    seen, stack = set(), [start]
    while stack:
        node = stack.pop()
        if node in seen or node in blocked:
            continue
        seen.add(node)
        stack.extend(adjacency.get(node, ()))
    return wanted <= seen



def _code_blocks(text, path):
    """Lex C per file; retain markers only inside a function and their own scope.

    Supported evidence forms are direct, assigned and serializer-checked calls. Declarations,
    strings, function definitions and calls in a subsequent scope are not evidence.
    This is deliberately not a general C compiler or a preprocessor evaluator.
    """
    lex = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'
                     r"'(?:\\.|[^'\\])*'|[A-Za-z_][A-Za-z0-9_]*|!=|==|[^\s]", re.S)
    marker_re = re.compile(r'/\*\s*train_node_id=(\d+)\s+kind=\d+\s+name=([^*]+?)\s*\*/')
    tokens, markers = [], []
    for match in lex.finditer(text):
        value = match.group()
        if value.startswith(('/*', '//')):
            marker = marker_re.fullmatch(value)
            if marker:
                markers.append((marker.group(1), marker.group(2).strip(), match.start(), match.end()))
            continue
        if value.startswith(('"', "'")):
            value = '__C_LITERAL__'
        tokens.append((value, match.start(), match.end()))
    stack, scopes, parens = [], [], {}
    opens = []
    for i, (value, start, end) in enumerate(tokens):
        if value == '(':
            opens.append(i)
        elif value == ')' and opens:
            parens[i] = opens.pop()
        elif value == '{':
            function = stack[-1][1] if stack else None
            if not stack and i and tokens[i - 1][0] == ')' and i - 1 in parens:
                before = parens[i - 1] - 1
                if before >= 0 and re.fullmatch(r'[A-Za-z_]\w*', tokens[before][0]):
                    function = tokens[before][0]
            stack.append((i, function))
        elif value == '}' and stack:
            opening, function = stack.pop()
            scopes.append((tokens[opening][1], start, function))
    found = []
    for index, (node_id, name, start, end) in enumerate(markers):
        owners = [scope for scope in scopes if scope[0] < start < scope[1] and scope[2]]
        if not owners:
            continue
        scope = max(owners, key=lambda entry: entry[0])
        previous = [token[0] for token in tokens if token[2] <= start]
        # A marker must precede a statement, not split a declaration/expression.
        if not previous or previous[-1] not in ('{', '}', ';'):
            continue
        stop = min(scope[1], markers[index + 1][2] if index + 1 < len(markers) else len(text))
        body = [token[0] for token in tokens if end <= token[1] < stop]
        found.append({'node_id': node_id, 'name': name, 'tokens': body,
                      'path': str(Path(path).resolve()), 'function': scope[2],
                      'line': text.count('\n', 0, start) + 1})
    return found


def _has_kernel_call(tokens, symbol):
    """Recognize Serializer CodeFunction/WithCheck/WithRet expression forms.

    Match a call, not a prototype/definition or unevaluated sizeof expression.
    Scope and file boundaries have already been enforced by _code_blocks.
    """
    for i, token in enumerate(tokens):
        if token != symbol or i + 1 >= len(tokens) or tokens[i + 1] != '(':
            continue
        start = i
        while start and tokens[start - 1] not in (';', '{', '}'):
            start -= 1
        prefix = tokens[start:i]
        direct = not prefix or prefix == ['return']
        assigned = (len(prefix) >= 2 and prefix[-1] == '=' and
                    all(re.fullmatch(r'[A-Za-z_]\w*|\*', t) for t in prefix[:-1]))
        checked = prefix == ['if', '(']
        if not (direct or assigned or checked):
            continue
        depth = 0
        for j in range(i + 1, len(tokens)):
            depth += (tokens[j] == '(') - (tokens[j] == ')')
            if depth == 0:
                tail = tokens[j + 1:]
                if (direct or assigned) and tail[:1] == [';']:
                    return True
                if (checked and len(tail) >= 4 and tail[0] in ('!=', '==') and
                        re.fullmatch(r'[A-Za-z_]\w*|0', tail[1]) and tail[2] == ')' and
                        tail[3] in ('{', 'return')):
                    return True
                break
    return False


def _check_barrier_source_model(path, expected_sha256, expectations, nodes, edges, unique, observed, source_targets):
    """Validate a declared non-differentiable boundary in hash-locked ONNX."""
    for ref in expectations.get('forward_refs', []):
        _require(isinstance(ref, dict) and isinstance(ref.get('name'), str) and ref['name'],
                 'barrier forward_refs entries require name')
        index = unique(ref['name'])
        requirement = ref.get('source_node')
        if requirement is not None:
            node = nodes[index]
            identity = {'name': node.name, 'op_type': node.op_type, 'domain': node.domain}
            _require(identity == requirement, f"barrier source identity mismatch: {ref['name']}")
    for path_spec in expectations.get('barrier_upstream_paths', []):
        target_name = path_spec.get('forward_target', {}).get('name')
        _require(target_name in source_targets, 'barrier source target is not declared')
        upstream = unique(path_spec.get('forward_upstream', {}).get('name'))
        _require(_reachable(edges, upstream, {source_targets[target_name]}),
                 f'barrier source upstream-to-target path missing: {target_name}')
    for path_spec in expectations.get('parallel_upstream_paths', []):
        sink = path_spec.get('forward_sink')
        _require(isinstance(sink, dict) and isinstance(sink.get('name'), str) and sink['name'],
                 'parallel source path requires forward_sink')
        upstream = unique(path_spec.get('forward_upstream', {}).get('name'))
        sink_index = unique(sink['name'])
        _require(_reachable(edges, upstream, {sink_index}),
                 f'parallel source upstream-to-sink path missing: {sink["name"]}')
    return {'status': 'PASS', 'gradient_barrier': True,
            'model': {'path': str(path), 'sha256': expected_sha256, 'bytes': Path(path).stat().st_size},
            'targets': observed}


def _check_barrier_training_graph(net, expectations, forward_path, training_path, code_paths,
                                  code_blocks, forward, training, fnodes, tnodes,
                                  fedges, tedges, loss_nodes):
    """Validate legal gradient termination at a declared non-differentiable boundary."""
    for ref in expectations.get('forward_refs', []):
        _find_label(fnodes, ref.get('name'), ref.get('primitive'))
        node, label = _find_label(tnodes, ref.get('name'), ref.get('primitive'), 'ForwardRef')
        _require('ForwardRef' in label, f"barrier node is not ForwardRef: {ref.get('name')}")
        _require(any(_reachable(tedges, node, loss_nodes) for _ in loss_nodes),
                 f"barrier forward-to-loss path missing: {ref.get('name')}")
    for target in expectations.get('targets', []):
        name = target.get('forward_name')
        _find_label(fnodes, name, target.get('forward_primitive'))
        _find_label(tnodes, name, target.get('forward_primitive'), 'ForwardRef')
    for spec in expectations.get('forbidden_backward_nodes', []):
        name = spec.get('name')
        hits = [(node, label) for node, label in tnodes.items()
                if name in _label_lines(label) and 'Backward' in _label_lines(label)]
        _require(not hits, f'illegal Backward node crosses the declared barrier: {name}')
    for spec in expectations.get('forbidden_parameter_grads', []):
        name = spec.get('name')
        hits = [node for node, label in tnodes.items()
                if name in _label_lines(label) and 'ParameterGrad' in _label_lines(label)]
        _require(not hits, f'illegal ParameterGrad before the declared barrier: {name}')
    for spec in expectations.get('forbidden_optimizers', []):
        name = spec.get('name')
        hits = [node for node, label in tnodes.items()
                if name in _label_lines(label) and 'Optimizer' in _label_lines(label)]
        _require(not hits, f'illegal optimizer before the declared barrier: {name}')
    marker = expectations.get('barrier_grad_slot_contains')
    _require(isinstance(marker, str) and marker, 'barrier_grad_slot_contains is required')
    slot_nodes = [node for node, label in tnodes.items() if marker in label.replace(chr(92) + chr(110), chr(10))]
    observed_paths = []
    for path_spec in expectations.get('parallel_upstream_paths', []):
        fup, _ = _find_label(fnodes, path_spec.get('forward_upstream', {}).get('name'),
                             path_spec.get('forward_upstream', {}).get('primitive'))
        fsink, _ = _find_label(fnodes, path_spec.get('forward_sink', {}).get('name'),
                               path_spec.get('forward_sink', {}).get('primitive'))
        _require(_reachable(fedges, fup, {fsink}), 'parallel forward path missing')
        tfup, _ = _find_label(tnodes, path_spec.get('forward_upstream', {}).get('name'),
                              path_spec.get('forward_upstream', {}).get('primitive'), 'ForwardRef')
        _require(any(_reachable(tedges, tfup, loss_nodes) for _ in loss_nodes),
                 'parallel forward-to-loss path missing')
        ub, ublabel = _find_label(tnodes, path_spec.get('upstream_backward', {}).get('name'),
                                  path_spec.get('upstream_backward', {}).get('primitive'), 'Backward')
        pg, _ = _find_label(tnodes, path_spec.get('parameter_grad', {}).get('name'), None, 'ParameterGrad')
        onode, olabel = _find_label(tnodes, path_spec.get('optimizer', {}).get('name'),
                                    path_spec.get('optimizer', {}).get('primitive'), 'Optimizer')
        _require(any(_reachable(tedges, loss, {ub}) for loss in loss_nodes),
                 'loss-to-parallel-backward path missing')
        _require(_reachable(tedges, ub, {pg}) and _reachable(tedges, pg, {onode}),
                 'parallel backward-to-optimizer path missing')
        observed_paths.append({'upstream_backward_node': ub, 'parameter_grad_node': pg,
                               'optimizer_node': onode, 'upstream_backward_label': ublabel,
                               'optimizer_label': olabel})
    for symbol in expectations.get('required_code_calls', []):
        _require(isinstance(symbol, str) and bool(symbol)
                 and any(_has_kernel_call(block['tokens'], symbol) for block in code_blocks),
                 f'required generated C call missing: {symbol}')
    evidence = [forward_path, training_path, *code_paths]
    return {'status': 'PASS', 'graph_expectations_version': 1, 'gradient_barrier': True,
            'targets': expectations.get('targets', []), 'barrier_grad_slot': marker,
            'parallel_upstream_paths': observed_paths,
            'evidence': [{'path': str(p.resolve()), 'bytes': p.stat().st_size,
                          'sha256': _sha256(p)} for p in evidence]}


def check_source_model(model_path, expected_sha256, expectations):
    """Independently parse the hash-locked ONNX, never infer source nodes from DOT.

    Version-1 cases identify source nodes by forward_name. source_node, when
    supplied, additionally requires an exact name/op_type/domain triple. Legacy
    cases still undergo parsing, schema validation, unique-name and source-path
    checks; their actual source triples are recorded, not guessed from primitives.
    """
    try:
        import onnx
    except ImportError as exc:
        raise ValueError('source ONNX validation requires the onnx Python dependency') from exc
    path = Path(model_path).resolve()
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected_sha256, 'source model hash mismatch')
    try:
        model = onnx.load_model_from_string(raw)
        # External tensor files would require their own identity evidence.
        _require(not any(t.external_data for t in model.graph.initializer),
                 'external-data ONNX models require separately locked tensor evidence')
        onnx.checker.check_model(model)
    except Exception as exc:
        raise ValueError(f'invalid source ONNX model: {exc}') from exc
    nodes = list(model.graph.node)
    def unique(name):
        matches = [i for i, node in enumerate(nodes) if node.name == name]
        _require(isinstance(name, str) and bool(name) and len(matches) == 1,
                 f'source ONNX node must uniquely match name={name!r}; got {len(matches)}')
        return matches[0]
    producer = {output: i for i, node in enumerate(nodes) for output in node.output if output}
    edges = [(producer[value], i) for i, node in enumerate(nodes)
             for value in node.input if value in producer]
    observed, source_targets = [], {}
    for target in expectations['targets']:
        requirement = target.get('source_node')
        if requirement is not None:
            _require(isinstance(requirement, dict) and set(requirement) == {'name', 'op_type', 'domain'}
                     and all(isinstance(v, str) for v in requirement.values())
                     and requirement['name'] and requirement['op_type'],
                     'source_node must declare name, op_type and domain')
        name = requirement['name'] if requirement is not None else target['forward_name']
        index = unique(name)
        node = nodes[index]
        identity = {'name': node.name, 'op_type': node.op_type, 'domain': node.domain}
        if requirement is not None:
            _require(identity == requirement, f'source ONNX identity mismatch: {name}')
        _require(target['forward_name'] not in source_targets, 'duplicate graph target expectation')
        source_targets[target['forward_name']] = index
        observed.append({'forward_name': target['forward_name'], **identity,
                         'declared_identity_checked': requirement is not None})
    if expectations.get('gradient_barrier') is True:
        return _check_barrier_source_model(path, expected_sha256, expectations,
                                           nodes, edges, unique, observed, source_targets)
    for path_spec in expectations['upstream_paths']:
        target_name = path_spec['forward_target']['name']
        _require(target_name in source_targets, 'source upstream path target is not declared')
        upstream = unique(path_spec['forward_upstream']['name'])
        _require(_reachable(edges, upstream, {source_targets[target_name]}),
                 f'source upstream-to-target path missing: {target_name}')
    return {'status': 'PASS', 'model': {'path': str(path), 'sha256': expected_sha256,
                                      'bytes': len(raw)}, 'targets': observed}


def _resolve_node(nodes, spec, role):
    _require(isinstance(spec, dict), f"{role} expectation must be an object")
    name = spec.get("name")
    primitive = spec.get("primitive")
    node, label = _find_label(nodes, name, primitive, spec.get("label_contains"))
    return node, label


def _code_node_id(node):
    match = re.search(r"_(\d+)$", node)
    _require(match, f"training node id missing: {node}")
    return match.group(1)


def check_training_graph(net, expectations):
    """Return auditable evidence or raise ValueError; no ONNX package is needed."""
    _require(isinstance(expectations, dict), "graph_expectations is required")
    _require(expectations.get("graph_expectations_version") == 1, "graph_expectations_version must be 1")
    targets = expectations.get("targets")
    _require(isinstance(targets, list) and targets, "graph_expectations.targets is required")
    upstream_paths = expectations.get("upstream_paths")
    if expectations.get("gradient_barrier") is not True:
        _require(isinstance(upstream_paths, list) and upstream_paths, "graph_expectations.upstream_paths is required")
    forward_path = Path(net) / "forward_graph.dot"
    training_path = Path(net) / "training_graph.dot"
    forward = _text(forward_path)
    training = _text(training_path)
    fnodes, tnodes = _nodes(forward), _nodes(training)
    fedges, tedges = _edges(forward), _edges(training)
    code_paths = list((Path(net) / "src").rglob("*.c"))
    _require(code_paths, "generated C source is missing")
    blocks = [block for p in code_paths
              for block in _code_blocks(p.read_text(encoding="utf-8-sig"), p)]
    loss_nodes = {n for n, label in tnodes.items() if "Loss" in _label_lines(label)}
    _require(loss_nodes, "training graph loss node is missing")
    if expectations.get("gradient_barrier") is True:
        return _check_barrier_training_graph(
            net, expectations, forward_path, training_path, code_paths, blocks,
            forward, training, fnodes, tnodes, fedges, tedges, loss_nodes)
    observed = []
    for target in targets:
        _require(isinstance(target, dict), "target expectation must be an object")
        name = target.get("forward_name")
        backward = target.get("backward_name", name)
        primitive = target.get("forward_primitive")
        _require(isinstance(name, str) and name and isinstance(backward, str) and backward, "target names are required")
        fnode, flabel = _find_label(fnodes, name, primitive)
        tforward, tflabel = _find_label(tnodes, name, primitive, "ForwardRef")
        tback, tblabel = _find_label(tnodes, backward, target.get("backward_primitive"), "Backward")
        _require("ForwardRef" in tflabel, f"training forward node is not ForwardRef: {name}")
        _require("Backward" in tblabel, f"training backward node is not Backward: {backward}")
        _require(loss_nodes and any(_reachable(tedges, loss, {tback}) for loss in loss_nodes),
                 f"loss-to-backward graph link missing: {name}")
        node_id = re.search(r"(?:train_node_id=|^|_)((?:\d+))", tback)
        _require(node_id, f"training node id missing in label: {backward}")
        matched = [block for block in blocks
                   if block["node_id"] == node_id.group(1) and block["name"] == backward]
        _require(len(matched) == 1, f"generated code block missing or ambiguous: {backward}")
        body = matched[0]["tokens"]
        symbols = target.get("backward_symbols", [])
        _require(isinstance(symbols, list) and symbols and all(isinstance(x, str) and x for x in symbols),
                 f"backward_symbols required: {backward}")
        _require(any(_has_kernel_call(body, symbol) for symbol in symbols),
                 f"declared backward call not found in generated code: {backward}")
        observed.append({"forward_node": fnode, "forward_label": flabel, "training_forward_node": tforward,
                         "backward_node": tback, "backward_label": tblabel, "train_node_id": int(node_id.group(1)),
                         "backward_symbols": symbols,
                         "code": {key: matched[0][key] for key in ("path", "function", "line")}})
    observed_paths = []
    _require(len({item["forward_node"] for item in observed}) == len(observed),
             "duplicate graph target expectation")
    for path in upstream_paths:
        _require(isinstance(path, dict) and isinstance(path.get("upstream_backward"), dict),
                 "upstream path requires upstream_backward")
        ub, ublabel = _find_label(tnodes, path["upstream_backward"].get("name"), path["upstream_backward"].get("primitive"), "Backward")
        _require("Backward" in ublabel, f"upstream node is not Backward: {ub}")
        optimizer = path.get("optimizer")
        onode, olabel = _find_label(tnodes, optimizer.get("name"), optimizer.get("primitive"), "Optimizer")
        _require("Optimizer" in olabel, f"upstream node is not Optimizer: {onode}")
        forward_upstream = path.get("forward_upstream")
        forward_target = path.get("forward_target")
        _require(isinstance(forward_upstream, dict) and isinstance(forward_target, dict),
                 "upstream path requires forward_upstream and forward_target")
        fup, _ = _find_label(fnodes, forward_upstream.get("name"), forward_upstream.get("primitive"))
        ft, _ = _find_label(fnodes, forward_target.get("name"), forward_target.get("primitive"))
        bound = [item for item in observed if item['forward_node'] == ft]
        _require(len(bound) == 1, 'upstream path must bind exactly one declared target')
        bound = bound[0]
        target_back_nodes = {bound['backward_node']}
        _require(_reachable(fedges, fup, {ft}), f"forward upstream-to-target path missing: {fup} -> {ft}")
        _require(any(_reachable(tedges, bound['training_forward_node'], {loss}) for loss in loss_nodes),
                 f"forward target-to-loss path missing: {ft}")
        parameter_nodes = {n for n, label in tnodes.items() if "ParameterGrad" in _label_lines(label)}
        _require(parameter_nodes, "training graph ParameterGrad node is missing")
        _require(any(_reachable(tedges, bound['backward_node'], {ub}) and
                     _reachable(tedges, ub, {parameter}) and
                     _reachable(tedges, parameter, {onode}) for parameter in parameter_nodes),
                 f"target-to-upstream-to-ParameterGrad-to-optimizer path missing: {ub}")
        _require(not any(_reachable(tedges, loss, {ub}, blocked=target_back_nodes)
                         for loss in loss_nodes),
                 f"upstream backward has a loss bypass around target: {ub}")
        observed_paths.append({"upstream_backward_node": ub, "optimizer_node": onode,
                               "upstream_backward_label": ublabel, "optimizer_label": olabel,
                               "target_nodes": sorted(target_back_nodes)})
    evidence = [forward_path, training_path, *code_paths]
    return {"status": "PASS", "graph_expectations_version": 1, "targets": observed, "upstream_paths": observed_paths,
            "evidence": [{"path": str(p.resolve()), "bytes": p.stat().st_size, "sha256": _sha256(p)} for p in evidence]}
