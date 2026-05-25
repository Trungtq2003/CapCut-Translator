import json
import copy
import uuid
import requests


LANGUAGES = {
    "CS": "Czech",
    "PL": "Polish",
    "RU": "Russian",
    "DE": "German",
    "NL": "Dutch",
    "HU": "Hungarian",
    "FR": "French",
    "ES": "Spanish",
}

def new_uuid():
    return str(uuid.uuid4()).upper()


def translate_text(text, target_lang, api_key=""):
    """Dùng MyMemory API - free, không cần key."""
    try:
        lang_map = {
            "CS": "cs", "PL": "pl", "RU": "ru", "DE": "de",
            "NL": "nl", "HU": "hu", "FR": "fr", "ES": "es",
        }
        target = lang_map.get(target_lang, target_lang.lower())
        res = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"en|{target}"},
            timeout=15
        )
        res.raise_for_status()
        result = res.json()["responseData"]["translatedText"]
        return result
    except Exception as e:
        raise RuntimeError(f"Lỗi dịch '{text[:30]}...': {e}")


def process(json_path, target_langs, api_key="", log_fn=None):
    """
    Đọc draft_content.json, dịch và thêm track mới cho mỗi ngôn ngữ.
    log_fn: callback(str) để ghi log ra UI.
    """

    def log(msg):
        if log_fn:
            log_fn(msg)

    # ── Đọc file ──────────────────────────────────────────────
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    materials = data["materials"]
    tracks = data["tracks"]

    # ── Lấy tất cả text track gốc ─────────────────────────────
    orig_text_tracks = [t for t in tracks if t.get("type") == "text"]
    if not orig_text_tracks:
        raise RuntimeError("Không tìm thấy text track trong file!")

    # Build map: material_id → text_material
    text_mat_map = {m["id"]: m for m in materials.get("texts", [])}

    # Build map: anim_id → anim_material
    anim_map = {a["id"]: a for a in materials.get("material_animations", [])}

    # Max render_index hiện tại
    max_ri = max(
        seg.get("render_index", 0)
        for t in tracks
        for seg in t.get("segments", [])
    )

    total = len(target_langs)
    for lang_idx, lang_code in enumerate(target_langs):
        lang_name = LANGUAGES.get(lang_code, lang_code)
        log(f"[{lang_idx+1}/{total}] Đang dịch sang {lang_name}...")

        new_text_mats = {}   # old_mat_id → new_mat_id
        new_anim_mats = {}   # old_anim_id → new_anim_id

        # ── Dịch và clone từng text material ──────────────────
        for orig_mat_id, orig_mat in text_mat_map.items():
            content_json = json.loads(orig_mat["content"])
            orig_text = content_json.get("text", "")

            # Dịch (giữ \n)
            lines = orig_text.split("\n")
            translated_lines = []
            for line in lines:
                if line.strip():
                    translated = translate_text(line, lang_code, api_key)
                    translated_lines.append(translated)
                else:
                    translated_lines.append(line)
            new_text = "\n".join(translated_lines)

            log(f"    '{orig_text[:25]}' → '{new_text[:25]}'")

            # Clone material
            new_mat = copy.deepcopy(orig_mat)
            new_mat_id = new_uuid()
            new_mat["id"] = new_mat_id

            content_json["text"] = new_text
            new_len = len(new_text)
            for style in content_json.get("styles", []):
                if "range" in style:
                    style["range"][1] = new_len
            new_mat["content"] = json.dumps(content_json, ensure_ascii=False)

            materials["texts"].append(new_mat)
            new_text_mats[orig_mat_id] = new_mat_id

        # ── Clone animation materials ──────────────────────────
        # Collect all anim refs used by text tracks
        all_anim_refs = set()
        for track in orig_text_tracks:
            for seg in track.get("segments", []):
                for ref in seg.get("extra_material_refs", []):
                    if ref in anim_map:
                        all_anim_refs.add(ref)

        for orig_anim_id in all_anim_refs:
            new_anim = copy.deepcopy(anim_map[orig_anim_id])
            new_anim_id = new_uuid()
            new_anim["id"] = new_anim_id
            materials["material_animations"].append(new_anim)
            new_anim_mats[orig_anim_id] = new_anim_id

        # ── Clone text tracks ──────────────────────────────────
        for orig_track in orig_text_tracks:
            new_track = copy.deepcopy(orig_track)
            new_track["id"] = new_uuid()

            new_segs = []
            for orig_seg in orig_track.get("segments", []):
                new_seg = copy.deepcopy(orig_seg)
                new_seg["id"] = new_uuid()

                # Trỏ tới text material mới
                old_mat_id = orig_seg["material_id"]
                new_seg["material_id"] = new_text_mats.get(old_mat_id, old_mat_id)

                # Trỏ tới anim material mới
                new_refs = []
                for ref in orig_seg.get("extra_material_refs", []):
                    new_refs.append(new_anim_mats.get(ref, ref))
                new_seg["extra_material_refs"] = new_refs

                # Tắt mặc định
                new_seg["visible"] = False

                # Tăng render_index
                max_ri += 1
                new_seg["render_index"] = max_ri

                new_segs.append(new_seg)

            new_track["segments"] = new_segs
            tracks.append(new_track)

        log(f"    ✓ {lang_name} xong!\n")

    # ── Ghi đè file ──────────────────────────────────────────────
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    log(f"✅ Đã ghi đè: {json_path}")
    return json_path
