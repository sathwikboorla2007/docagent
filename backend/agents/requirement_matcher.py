import os
import yaml
import ast
import operator as op
from typing import Dict, List, Any
from backend.schemas import RequirementChecklist, RequirementItem

class RequirementMatcher:
    def __init__(self, config_dir: str = 'config/domains'):
        # resolve config_dir relative to project root
        # If __file__ is backend/agents/requirement_matcher.py, root is two levels up
        self.config_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            config_dir
        )
        self.configs: Dict[str, dict] = {}
        self.load_configs()

    def load_configs(self):
        if not os.path.exists(self.config_dir):
            return
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                path = os.path.join(self.config_dir, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'domain' in config:
                        self.configs[config['domain']] = config

    def _safe_eval(self, expression: str, context: dict) -> bool:
        """
        Simple expression evaluator supporting: >, <, >=, <=, ==, !=, and, or
        Substitutes context variables into expression. No eval/exec.
        """
        if context is None:
            context = {}
            
        operators = {
            ast.Gt: op.gt,
            ast.Lt: op.lt,
            ast.GtE: op.ge,
            ast.LtE: op.le,
            ast.Eq: op.eq,
            ast.NotEq: op.ne,
            ast.And: lambda a, b: a and b,
            ast.Or: lambda a, b: a or b,
        }

        def eval_node(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                if node.id in context:
                    return context[node.id]
                elif node.id == 'true' or node.id == 'True':
                    return True
                elif node.id == 'false' or node.id == 'False':
                    return False
                return None
            elif isinstance(node, ast.Compare):
                left = eval_node(node.left)
                for op_node, comparator in zip(node.ops, node.comparators):
                    right = eval_node(comparator)
                    operator_func = operators.get(type(op_node))
                    if not operator_func:
                        return False
                    if not operator_func(left, right):
                        return False
                    left = right
                return True
            elif isinstance(node, ast.BoolOp):
                values = [eval_node(v) for v in node.values]
                if isinstance(node.op, ast.And):
                    return all(values)
                elif isinstance(node.op, ast.Or):
                    return any(values)
            elif isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                if isinstance(node.op, ast.Mult):
                    return (left or 0) * (right or 0)
                elif isinstance(node.op, ast.Add):
                    return (left or 0) + (right or 0)
                elif isinstance(node.op, ast.Sub):
                    return (left or 0) - (right or 0)
                elif isinstance(node.op, ast.Div):
                    if right == 0:
                        return 0
                    return (left or 0) / (right or 0)
            return False

        try:
            tree = ast.parse(expression, mode='eval')
            return bool(eval_node(tree.body))
        except Exception:
            return False

    def get_requirements(self, domain: str, context: dict = None) -> RequirementChecklist:
        if domain not in self.configs:
            raise ValueError(f"Domain {domain} not found")
            
        config = self.configs[domain]
        context = context or {}
        
        required_docs = []
        for doc in config.get('required_documents', []):
            item = RequirementItem(
                doc_type=doc.get('type'),
                description=doc.get('description'),
                is_conditional=False
            )
            required_docs.append(item)
            
        conditional_docs = []
        for cond_req in config.get('conditional_requirements', []):
            condition = cond_req.get('condition')
            if self._safe_eval(condition, context):
                for doc in cond_req.get('then_require', []):
                    item = RequirementItem(
                        doc_type=doc.get('type'),
                        description=doc.get('description'),
                        is_conditional=True,
                        condition_expr=condition
                    )
                    conditional_docs.append(item)
                    
        return RequirementChecklist(
            domain=domain,
            display_name=config.get('display_name', domain),
            required_documents=required_docs,
            conditional_requirements=conditional_docs
        )

    def evaluate_eligibility(self, domain: str, context: dict) -> dict:
        if domain not in self.configs:
            raise ValueError(f"Domain {domain} not found")
            
        config = self.configs[domain]
        context = context or {}
        
        checks = []
        all_passed = True
        
        for rule_obj in config.get('eligibility_rules', []):
            rule_expr = rule_obj.get('rule')
            passed = self._safe_eval(rule_expr, context)
            if not passed:
                all_passed = False
            checks.append({
                'rule': rule_expr,
                'passed': passed,
                'message': rule_obj.get('message')
            })
            
        return {
            'eligible': all_passed,
            'checks': checks
        }

    def list_domains(self) -> List[str]:
        return list(self.configs.keys())
