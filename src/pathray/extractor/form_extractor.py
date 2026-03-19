"""Form extractor for HTML pages."""

from playwright.async_api import Page

from pathray.models.page_data import FormData, FormField


async def extract_forms(page: Page) -> list[FormData]:
    """Extract all forms and their fields from the page."""
    forms = await page.query_selector_all("form")
    if not forms:
        return []

    results: list[FormData] = []

    for form in forms:
        action = await form.get_attribute("action")
        method_raw = await form.get_attribute("method")
        method = (method_raw or "GET").upper()

        fields: list[FormField] = []
        field_elements = await form.query_selector_all("input, select, textarea")

        for el in field_elements:
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            name = (await el.get_attribute("name")) or ""
            required = await el.evaluate("el => el.required")

            if tag == "select":
                field_type = "select"
                option_els = await el.query_selector_all("option")
                options = []
                for opt in option_els:
                    val = await opt.get_attribute("value")
                    text = (await opt.inner_text()).strip()
                    options.append(val if val is not None else text)
            elif tag == "textarea":
                field_type = "textarea"
                options = []
            else:
                field_type = (await el.get_attribute("type")) or "text"
                options = []

            placeholder = await el.get_attribute("placeholder")

            # Find label via label[for=id]
            label = None
            el_id = await el.get_attribute("id")
            if el_id:
                label_el = await form.query_selector(f'label[for="{el_id}"]')
                if label_el:
                    label = (await label_el.inner_text()).strip() or None

            fields.append(
                FormField(
                    name=name,
                    field_type=field_type,
                    label=label,
                    required=bool(required),
                    placeholder=placeholder,
                    options=options,
                )
            )

        results.append(FormData(action=action, method=method, fields=fields))

    return results
