"""Tests for form extractor."""

from unittest.mock import AsyncMock

import pytest

from pathray.extractor.form_extractor import extract_forms


def _make_option(value: str | None, text: str) -> AsyncMock:
    opt = AsyncMock()
    opt.get_attribute = AsyncMock(return_value=value)
    opt.inner_text = AsyncMock(return_value=text)
    return opt


def _make_field(
    tag: str,
    name: str = "",
    field_type: str | None = "text",
    required: bool = False,
    el_id: str | None = None,
    options: list[tuple[str | None, str]] | None = None,
) -> AsyncMock:
    el = AsyncMock()

    async def _evaluate(expr: str) -> object:
        if "tagName" in expr:
            return tag
        return required

    async def _get_attr(attr: str) -> str | None:
        if attr == "name":
            return name
        if attr == "type":
            return field_type
        if attr == "id":
            return el_id
        return None

    el.evaluate = AsyncMock(side_effect=_evaluate)
    el.get_attribute = AsyncMock(side_effect=_get_attr)

    if tag == "select" and options is not None:
        opt_els = [_make_option(v, t) for v, t in options]
        el.query_selector_all = AsyncMock(return_value=opt_els)
    else:
        el.query_selector_all = AsyncMock(return_value=[])

    return el


def _make_label(text: str) -> AsyncMock:
    label = AsyncMock()
    label.inner_text = AsyncMock(return_value=text)
    return label


def _make_form(
    action: str | None,
    method: str | None,
    fields: list[AsyncMock],
    labels: dict[str, AsyncMock] | None = None,
) -> AsyncMock:
    form = AsyncMock()

    async def _get_attr(attr: str) -> str | None:
        if attr == "action":
            return action
        if attr == "method":
            return method
        return None

    form.get_attribute = AsyncMock(side_effect=_get_attr)
    form.query_selector_all = AsyncMock(return_value=fields)

    async def _query_selector(selector: str) -> AsyncMock | None:
        if labels:
            for el_id, label in labels.items():
                if f'[for="{el_id}"]' in selector:
                    return label
        return None

    form.query_selector = AsyncMock(side_effect=_query_selector)
    return form


def _make_page(forms: list[AsyncMock]) -> AsyncMock:
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=forms)
    return page


@pytest.mark.asyncio
async def test_no_forms_returns_empty():
    page = _make_page([])
    result = await extract_forms(page)
    assert result == []


@pytest.mark.asyncio
async def test_form_action_and_method():
    form = _make_form(action="/submit", method="post", fields=[])
    page = _make_page([form])
    result = await extract_forms(page)
    assert len(result) == 1
    assert result[0].action == "/submit"
    assert result[0].method == "POST"


@pytest.mark.asyncio
async def test_form_method_defaults_to_get():
    form = _make_form(action=None, method=None, fields=[])
    page = _make_page([form])
    result = await extract_forms(page)
    assert result[0].method == "GET"
    assert result[0].action is None


@pytest.mark.asyncio
async def test_input_text_field():
    field = _make_field(tag="input", name="username", field_type="text")
    form = _make_form(action="/login", method="post", fields=[field])
    page = _make_page([form])
    result = await extract_forms(page)
    assert len(result[0].fields) == 1
    f = result[0].fields[0]
    assert f.name == "username"
    assert f.field_type == "text"
    assert f.required is False
    assert f.label is None
    assert f.options == []


@pytest.mark.asyncio
async def test_various_input_types():
    fields = [
        _make_field(tag="input", name="email", field_type="email"),
        _make_field(tag="input", name="password", field_type="password"),
        _make_field(tag="input", name="age", field_type="number"),
        _make_field(tag="input", name="subscribe", field_type="checkbox"),
    ]
    form = _make_form(action="/", method=None, fields=fields)
    page = _make_page([form])
    result = await extract_forms(page)
    field_types = [f.field_type for f in result[0].fields]
    assert field_types == ["email", "password", "number", "checkbox"]


@pytest.mark.asyncio
async def test_required_attribute():
    field = _make_field(tag="input", name="email", field_type="email", required=True)
    form = _make_form(action="/", method=None, fields=[field])
    page = _make_page([form])
    result = await extract_forms(page)
    assert result[0].fields[0].required is True


@pytest.mark.asyncio
async def test_not_required_by_default():
    field = _make_field(tag="input", name="nickname", field_type="text", required=False)
    form = _make_form(action="/", method=None, fields=[field])
    page = _make_page([form])
    result = await extract_forms(page)
    assert result[0].fields[0].required is False


@pytest.mark.asyncio
async def test_select_with_options():
    field = _make_field(
        tag="select",
        name="country",
        options=[("us", "United States"), ("kr", "Korea"), (None, "Other")],
    )
    form = _make_form(action="/", method=None, fields=[field])
    page = _make_page([form])
    result = await extract_forms(page)
    f = result[0].fields[0]
    assert f.field_type == "select"
    assert f.name == "country"
    assert f.options == ["us", "kr", "Other"]


@pytest.mark.asyncio
async def test_textarea_field():
    field = _make_field(tag="textarea", name="message")
    form = _make_form(action="/", method=None, fields=[field])
    page = _make_page([form])
    result = await extract_forms(page)
    f = result[0].fields[0]
    assert f.field_type == "textarea"
    assert f.name == "message"
    assert f.options == []


@pytest.mark.asyncio
async def test_label_mapping():
    field = _make_field(tag="input", name="email", field_type="email", el_id="email-input")
    label = _make_label("Email Address")
    form = _make_form(
        action="/",
        method=None,
        fields=[field],
        labels={"email-input": label},
    )
    page = _make_page([form])
    result = await extract_forms(page)
    assert result[0].fields[0].label == "Email Address"


@pytest.mark.asyncio
async def test_no_label_when_no_id():
    field = _make_field(tag="input", name="name", field_type="text", el_id=None)
    form = _make_form(action="/", method=None, fields=[field])
    page = _make_page([form])
    result = await extract_forms(page)
    assert result[0].fields[0].label is None


@pytest.mark.asyncio
async def test_multiple_forms():
    form1 = _make_form(action="/login", method="post", fields=[])
    form2 = _make_form(action="/search", method="get", fields=[])
    page = _make_page([form1, form2])
    result = await extract_forms(page)
    assert len(result) == 2
    assert result[0].action == "/login"
    assert result[1].action == "/search"
