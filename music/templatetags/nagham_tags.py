from django import template


register = template.Library()


@register.inclusion_tag("partials/banner_slot.html", takes_context=True)
def render_banner_slot(context, slot_name):
    slots = context.get("page_banner_slots", {})
    return {
        "banners": slots.get(slot_name, []),
        "slot_name": slot_name,
    }
