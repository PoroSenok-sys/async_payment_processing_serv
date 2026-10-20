from typing import Annotated

from pydantic import AnyHttpUrl, UrlConstraints

WebhookUrl = Annotated[AnyHttpUrl, UrlConstraints(host_required=True)]
