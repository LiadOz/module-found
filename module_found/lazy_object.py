from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI


class APICtx:
    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None

    @property
    def client(self):
        assert self._client, "API key not set"
        return self._client

    def set_api_key(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

ctx = APICtx()

class LazyModule:
    def __init__(self, api_key: str, name: str) -> None:
        self._api_key = api_key
        self.name = name
        module_code = _generate_initial_module(name)
        self._values: Dict[str, Any] = {}
        self._existing_lines: List[str] = []
        self.add_code(module_code)

    def __getattr__(self, name: str) -> Any:
        existing = self._values.get(name, None)
        if existing:
            return existing
        if name.upper() == name:
            value = self._generate_constant(name)
            self._values[name] = value
        else:
            value = self._generate_function(name)
        return value

    def _generate_constant(self, constant_name: str) -> Any:
        constant_string = _generate_constant(self, constant_name)
        self.add_code(constant_string)
        return self._values[constant_name]

    def _generate_function(self, function_name: str) -> Callable:
        return LazyFunction(function_name, self)

    @property
    def code(self):
        return '\n'.join(self._existing_lines)

    def add_code(self, code: str):
        exec(code, self._values)  # pylint: disable=exec-used
        self._existing_lines.extend(code.splitlines())
        self._existing_lines.append('')

    def get_value(self, name: str) -> Any:
        return self._values[name]


class LazyFunction:  # pylint: disable=too-few-public-methods
    def __init__(self, name: str, parent_module: LazyModule) -> None:
        self.name = name
        self._parent_module = parent_module
        self._generated_function: Optional[Callable] = None

    def __call__(self, *args, **kwargs) -> Any:
        if self._generated_function:
            return self._generated_function(*args, **kwargs)

        func_string = _generate_function(self._parent_module, self.name, *args, **kwargs)
        self._parent_module.add_code(func_string)
        generated_func = self._parent_module.get_value(self.name)
        self._generated_function = generated_func
        return generated_func(*args, **kwargs)


def _remove_formatting(message: str) -> str:
    message = message.replace('```python\n', '')
    message = message.replace('\n```', '')
    return message


# pylint: disable=line-too-long
MODEL = "gpt-3.5-turbo"
SYSTEM_PREFIX = "You are a python code generator, every response will be evaluated by exec statement."
def _generate_initial_module(module_name) -> str:
    completion = ctx.client.chat.completions.create(
      model=MODEL,
      messages=[
        {"role": "system", "content": f"{SYSTEM_PREFIX} you will be given a module name, you should generate the base code needed for the module, later more code will be added that may or may not use it. You are not allowed to import modules that are not in the standard library, as they won't be available"},
        {"role": "user", "content": f"module name is {module_name}"}
      ]
    )
    return _remove_formatting(completion.choices[0].message.content)


def _generate_constant(module: LazyModule, constant_name: str) -> str:
    completion = ctx.client.chat.completions.create(
      model=MODEL,
      messages=[
        {"role": "system", "content": f"{SYSTEM_PREFIX} you will be given a module name, the module code, and a constant name separated by ;. you MUST give back a line that assigns a value to that exact constant name. You should always respond with whatever will fit the constant name and the module content the most"},
        {"role": "user", "content": f"module name is: {module.name};module code: {module.code};constant name: {constant_name}"}
      ]
    )
    return _remove_formatting(completion.choices[0].message.content)


def _generate_function(module: LazyModule, function_name: str, *used_args, **used_kwargs) -> str:
    completion = ctx.client.chat.completions.create(
      model=MODEL,
      messages=[
        {"role": "system", "content": f"""{SYSTEM_PREFIX} you will be given a module name, the module code, function name, EXAMPLE args and kwargs separated by ;.
You MUST follow ALL of the following rules.
1. The result must contain function definition of the requested function.
2. You MUST write the function that should work with the example args and kwargs, you can decide that the function may get additional kwargs but not new args.
3. You should always respond with whatever will fit both the function name and the module content the most.
4. You MAY import additional modules that exist in the stanard library but you MUST use them if you do.
5. Don't import modules that are already imported.
6. You must complete the function logic, no TODO comments or print statement saying some logic should be added later.
7. The result may only include imports if used and the target function definition
8. You are not allowed to show the usage of the function or add any code that is not an import or definition"""},
        {"role": "user", "content": f"module name is: {module.name};module code: {module.code};function name: {function_name};example args: {used_args};example kwargs: {used_kwargs}"}
      ]
    )
    return _remove_formatting(completion.choices[0].message.content)
