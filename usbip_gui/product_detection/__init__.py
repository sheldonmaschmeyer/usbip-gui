"""Product detection module."""

from .product_detection import (
    ItemUpdater,
    enrich_device_item,
    enrich_remote_device_item,
    extract_unknown_product_suffix,
    is_unknown_product,
    read_local_usb_descriptor_details,
    usb_details_script_path,
)

__all__ = [
    "ItemUpdater",
    "enrich_device_item",
    "enrich_remote_device_item",
    "extract_unknown_product_suffix",
    "is_unknown_product",
    "read_local_usb_descriptor_details",
    "usb_details_script_path",
]
