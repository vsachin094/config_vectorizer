# main_ingest.py
import logging
from config_loader import list_config_files, read_config, infer_device_name, infer_vendor
from masking import normalize_and_mask
from sectioner import section_config
from embeddings import embed_sections
from redis_store import store_sections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

def process_all_configs():
    paths = list_config_files()
    logging.info("Found %d config files", len(paths))

    for path in paths:
        try:
            raw = read_config(path)
            device_name = infer_device_name(path)
            vendor = infer_vendor(raw)
            logging.info("Processing %s (vendor=%s)", device_name, vendor)

            masked = normalize_and_mask(raw)
            sections = section_config(masked, device_name, vendor, path)
            if not sections:
                logging.warning("No sections for %s", device_name)
                continue

            embed_sections(sections)
            store_sections(sections)
            logging.info("Ingested %d sections for %s", len(sections), device_name)
        except Exception as exc:
            logging.exception("Failed processing %s: %s", path, exc)

if __name__ == "__main__":
    process_all_configs()
