from typing import Any

from jinja2 import Environment, StrictUndefined


env = Environment(undefined=StrictUndefined)


def render_template(template_body: str, context: dict[str, Any]) -> str:
    template = env.from_string(template_body)
    rendered_text = template.render(**context)
    return rendered_text


if __name__ == "__main__":
    result = render_template(
        template_body="Hello {{ username }}, booking #{{ booking_id }} is confirmed.",
        context={
            "username": "Ilya",
            "booking_id": 12345,
        }
    )
    print(result)