"""AST and regex-based code intelligence extracting functions, classes, imports, and docstrings."""

import ast
import logging
import re
from app.knowledge.schemas import CodeDependency, CodeSymbol

logger = logging.getLogger("kairo.knowledge.repositories.code_intel")


class CodeIntelligence:
    """Extracts structural symbols, signatures, and docstrings from source code."""

    def extract_symbols(
        self,
        code: str,
        file_path: str,
        language: str = "python",
    ) -> list[CodeSymbol]:
        """Parse source code and return a list of extracted symbols."""
        if language.lower() == "python" or file_path.endswith(".py"):
            return self._extract_python_ast(code, file_path)
        elif language.lower() in {"typescript", "javascript"} or file_path.endswith((".ts", ".js", ".tsx", ".jsx")):
            return self._extract_javascript_symbols(code, file_path, language)
        else:
            return self._extract_generic_symbols(code, file_path, language)

    def _extract_python_ast(self, code: str, file_path: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError as e:
            logger.debug(f"Syntax error parsing {file_path}: {e}")
            return self._extract_generic_symbols(code, file_path, "python")

        lines = code.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                # Form signature
                base_names = [ast.unparse(b) for b in node.bases]
                sig = f"class {node.name}({', '.join(base_names)}):"
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        type="CLASS",
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        signature=sig,
                        docstring=doc,
                        language="python",
                    )
                )

                # Extract class methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(item)
                        is_async = isinstance(item, ast.AsyncFunctionDef)
                        args = ast.unparse(item.args)
                        ret_ann = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                        m_sig = f"{'async ' if is_async else ''}def {item.name}({args}){ret_ann}:"
                        symbols.append(
                            CodeSymbol(
                                name=f"{node.name}.{item.name}",
                                type="METHOD",
                                file_path=file_path,
                                start_line=item.lineno,
                                end_line=getattr(item, "end_lineno", item.lineno),
                                signature=m_sig,
                                docstring=method_doc,
                                parent_symbol=node.name,
                                language="python",
                            )
                        )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not already captured as methods)
                # We check parent or lineno scope
                # If node has no parent class in ancestors
                is_async = isinstance(node, ast.AsyncFunctionDef)
                args = ast.unparse(node.args)
                ret_ann = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                sig = f"{'async ' if is_async else ''}def {node.name}({args}){ret_ann}:"
                doc = ast.get_docstring(node)
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        type="FUNCTION",
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        signature=sig,
                        docstring=doc,
                        language="python",
                    )
                )

        # De-duplicate symbols with same name and start_line
        seen: set[tuple[str, int]] = set()
        deduped: list[CodeSymbol] = []
        for s in symbols:
            key = (s.name, s.start_line)
            if key not in seen:
                seen.add(key)
                deduped.append(s)

        return deduped

    def _extract_javascript_symbols(self, code: str, file_path: str, lang: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        lines = code.splitlines()

        # Regex patterns for functions and classes
        fn_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)")
        arrow_pattern = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>")
        class_pattern = re.compile(r"^\s*(?:export\s+)?class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$]+))?")

        for idx, line in enumerate(lines, start=1):
            m_fn = fn_pattern.match(line)
            if m_fn:
                name, args = m_fn.group(1), m_fn.group(2)
                symbols.append(
                    CodeSymbol(
                        name=name,
                        type="FUNCTION",
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,  # approximate
                        signature=f"function {name}({args})",
                        language=lang,
                    )
                )
                continue

            m_arrow = arrow_pattern.match(line)
            if m_arrow:
                name, args = m_arrow.group(1), m_arrow.group(2)
                symbols.append(
                    CodeSymbol(
                        name=name,
                        type="FUNCTION",
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 10,
                        signature=f"const {name} = ({args}) =>",
                        language=lang,
                    )
                )
                continue

            m_cls = class_pattern.match(line)
            if m_cls:
                name = m_cls.group(1)
                extends = f" extends {m_cls.group(2)}" if m_cls.group(2) else ""
                symbols.append(
                    CodeSymbol(
                        name=name,
                        type="CLASS",
                        file_path=file_path,
                        start_line=idx,
                        end_line=idx + 20,
                        signature=f"class {name}{extends}",
                        language=lang,
                    )
                )

        return symbols

    def _extract_generic_symbols(self, code: str, file_path: str, lang: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith(("fn ", "func ", "def ", "sub ", "void ", "int ", "public ")):
                parts = stripped.split("(")
                if len(parts) > 1:
                    name_part = parts[0].split()[-1]
                    symbols.append(
                        CodeSymbol(
                            name=name_part,
                            type="FUNCTION",
                            file_path=file_path,
                            start_line=idx,
                            end_line=idx + 5,
                            signature=parts[0] + "(...)",
                            language=lang,
                        )
                    )
        return symbols

    def extract_dependencies(self, code: str, file_path: str) -> list[CodeDependency]:
        """Extract import statements and build file dependencies."""
        deps: list[CodeDependency] = []
        if file_path.endswith(".py"):
            try:
                tree = ast.parse(code, filename=file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            deps.append(
                                CodeDependency(
                                    source_file=file_path,
                                    target_file=alias.name.replace(".", "/") + ".py",
                                    dependency_type="IMPORTS",
                                )
                            )
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        target = mod.replace(".", "/") + ".py"
                        for alias in node.names:
                            deps.append(
                                CodeDependency(
                                    source_file=file_path,
                                    target_file=target,
                                    target_symbol=alias.name,
                                    dependency_type="IMPORTS",
                                )
                            )
            except Exception:
                pass
        return deps
