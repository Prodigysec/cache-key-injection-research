"""Small VCL lexer/parser and bounded path interpreter, not a full VCL validator.

Upstream Varnish VRT_hashdata frames EVERY call. Only strands within one
call can have ambiguous boundaries. Fastly is a different implementation.
"""
import ast
import re
from pathlib import Path

LEX = re.compile(r'\s+|/\*.*?\*/|//[^\n]*|\#[^\n]*|"(?:\\.|[^"\\])*"|[A-Za-z_][\w.-]*|[{}();+]|[^\s]', re.S)


def tokens(text):
    return [(m.group(), text.count('\n', 0, m.start()) + 1) for m in LEX.finditer(text)
            if not m.group().isspace() and not m.group().startswith(('/*', '//', '#'))]


class Parser:
    def __init__(self, text):
        self.ts = tokens(text)
        self.i = 0

    def peek(self):
        return self.ts[self.i][0] if self.i < len(self.ts) else ''

    def take(self, wanted=None):
        if not self.peek():
            raise ValueError('unexpected end of VCL')
        token = self.ts[self.i]
        if wanted is not None and token[0] != wanted:
            raise ValueError(f'line {token[1]}: expected {wanted}, got {token[0]}')
        self.i += 1
        return token

    def group(self):
        self.take('(')
        result, depth = [], 1
        while depth:
            tok = self.take()
            if tok[0] == '(':
                depth += 1
            elif tok[0] == ')':
                depth -= 1
            if depth:
                result.append(tok)
        return result

    def conditional(self):
        line = self.take()[1]
        condition = self.group()
        yes = self.block()
        no = []
        if self.peek() in ('else', 'elsif', 'elseif', 'elif'):
            if self.peek() == 'else':
                self.take()
                no = [self.conditional()] if self.peek() == 'if' else self.block()
            else:
                no = [self.conditional()]
        return ('if', condition, yes, no, line)

    def block(self):
        self.take('{')
        result = []
        while self.peek() != '}':
            name, line = self.ts[self.i] if self.peek() else ('', 0)
            if name == 'if':
                result.append(self.conditional())
            elif name == 'hash_data':
                self.take()
                expr = self.group()
                self.take(';')
                result.append(('hash', expr, line))
            elif name == 'call':
                self.take()
                result.append(('call', self.take()[0], line))
                self.take(';')
            elif name == 'return':
                self.take()
                result.append(('return', self.group(), line))
                self.take(';')
            else:
                # Explicitly retain unsupported statements; never silently certify them.
                unknown = []
                while self.peek() not in (';', '}'):
                    if not self.peek():
                        raise ValueError('unterminated block')
                    if self.peek() == '{':
                        self.block()
                        break
                    unknown.append(self.take())
                if self.peek() == ';':
                    self.take()
                result.append(('unknown', unknown, line))
        self.take('}')
        return result

    def subs(self):
        result = {}
        while self.peek():
            if self.peek() == 'sub':
                self.take()
                name = self.take()[0]
                if name in result:
                    raise ValueError(f'duplicate sub {name}: concatenate externally before analysis')
                result[name] = self.block()
            elif self.peek() == '{':
                self.block()
            else:
                self.take()
        return result


def expression_boundaries(expr):
    """Accept the string-strands subset: literal/variable joined by +."""
    parts = [value for value, _ in expr]
    if not parts or any(parts[i] != '+' for i in range(1, len(parts), 2)):
        return [], True
    atoms = parts[::2]
    if any(not (s.startswith('"') or re.fullmatch(r'[A-Za-z_][\w.-]*', s)) for s in atoms):
        return [], True
    findings, previous, separator = [], None, ''
    for atom in atoms:
        if atom.startswith('"'):
            separator += ast.literal_eval(atom)
        else:
            if previous and atom != previous and previous.startswith('req.') and atom.startswith('req.'):
                findings.append({'left': previous, 'right': atom, 'separator': separator,
                                 'score': 'NONE' if not separator else 'WEAK'})
            previous, separator = atom, ''
    return findings, False


def lint(path, max_paths=256):
    subs = Parser(Path(path).read_text(encoding='utf-8')).subs()
    findings = []
    def record(line, score, message, **properties):
        findings.append(dict(path=str(path), line=line, score=score, message=message,
                             rule='vcl-key-boundary-' + score.lower(), **properties))
    def execute(block, states, stack):
        for statement in block:
            kind = statement[0]
            active = [s for s in states if not s['terminal']]
            stopped = [s for s in states if s['terminal']]
            if not active:
                break
            if kind == 'if':
                states = stopped + execute(statement[2], [dict(s) for s in active], stack) + execute(statement[3], [dict(s) for s in active], stack)
            elif kind == 'call':
                name = statement[1]
                if name in stack or name not in subs:
                    record(statement[2], 'UNKNOWN', f'unresolved/recursive call {name}')
                else:
                    states = stopped + execute(subs[name], active, stack + [name])
            elif kind == 'return':
                states = stopped + [{**s, 'terminal': True} for s in active]
            elif kind == 'hash':
                boundaries, unknown = expression_boundaries(statement[1])
                if unknown:
                    record(statement[2], 'UNKNOWN', 'hash expression outside supported strands subset')
                for boundary in boundaries:
                    record(statement[2], boundary['score'],
                           f"{boundary['left']} → {boundary['right']}: {boundary['score']} within one hash_data call; lead only", **{k: v for k, v in boundary.items() if k != 'score'})
                # No cross-call concatenation: VRT_hashdata adds a field separator.
            elif kind == 'unknown':
                record(statement[2], 'UNKNOWN', 'unsupported statement in reachable hash subroutine')
            if len(states) > max_paths:
                raise ValueError(f'path limit {max_paths} exceeded')
        return states
    if 'vcl_hash' in subs:
        states = execute(subs['vcl_hash'], [{'terminal': False}], ['vcl_hash'])
        # On fallthrough upstream builtin hashes URL and Host/server IP in
        # distinct framed calls. That introduces no ambiguous call boundary.
        builtin_appended = any(not s['terminal'] for s in states)
    else:
        builtin_appended = True
    unique = {(f['line'], f['message']): {**f, 'builtin_appended_on_some_path': builtin_appended} for f in findings}
    return list(unique.values())
