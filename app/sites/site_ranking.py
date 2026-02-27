import math
from datetime import datetime

from web.backend.pro_user import ProUser


class SiteRankingManager:
    @staticmethod
    def _parse_datetime(dt):
        if not dt:
            return None
        if isinstance(dt, datetime):
            return dt
        dt_str = str(dt).strip()
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"]:
            try:
                return datetime.strptime(dt_str, fmt)
            except Exception:
                continue
        return None

    @staticmethod
    def _to_float(value, default=0.0):
        try:
            f = float(value)
            if math.isinf(f) or math.isnan(f):
                return default
            return f
        except Exception:
            return default

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    def get_site_ranking_info(self, site_name=None, site_url=None, siteid=None):
        info = ProUser().get_site_user_ranking_info(name=site_name, domain=site_url, siteid=siteid)
        if not info:
            return None
        if not info.get("enabled"):
            return None
        return info

    @staticmethod
    def _find_level(level_name, ranking_system):
        if not ranking_system:
            return None
        levels = ranking_system.get("levels") or []
        if not level_name:
            return None
        for level in levels:
            if level.get("name") == level_name:
                return level
        lowered = str(level_name).strip().lower()
        for level in levels:
            if str(level.get("name", "")).strip().lower() == lowered:
                return level
        return None

    @staticmethod
    def _find_special_level(level_name, ranking_system):
        special_levels = (ranking_system or {}).get("special_levels") or []
        if not level_name:
            return None
        for level in special_levels:
            if level.get("name") == level_name:
                return level
        lowered = str(level_name).strip().lower()
        for level in special_levels:
            if str(level.get("name", "")).strip().lower() == lowered:
                return level
        return None

    @staticmethod
    def _sorted_levels(ranking_system):
        return sorted((ranking_system or {}).get("levels") or [], key=lambda x: x.get("order", 0))

    @classmethod
    def _build_level_steps(cls, ranking_system, current_level_name, next_level_name=None, keep_account_level=None):
        steps = []
        levels = cls._sorted_levels(ranking_system)
        lowered_current = (current_level_name or "").strip().lower()
        lowered_next = (next_level_name or "").strip().lower()
        lowered_keep = (keep_account_level or "").strip().lower()
        current_idx = -1
        next_idx = -1
        for idx, level in enumerate(levels):
            name = level.get("name") or "-"
            lowered_name = str(name).strip().lower()
            if lowered_name == lowered_current:
                current_idx = idx
            if lowered_name == lowered_next:
                next_idx = idx

        for idx, level in enumerate(levels):
            name = level.get("name") or "-"
            lowered_name = str(name).strip().lower()
            state = "locked"
            if current_idx >= 0 and idx < current_idx:
                state = "done"
            elif idx == current_idx:
                state = "current"
            elif idx == next_idx:
                state = "target"
            steps.append({
                "name": name,
                "state": state,
                "order": level.get("order", idx),
                "is_keep": lowered_keep and lowered_name == lowered_keep
            })
        return steps

    @classmethod
    def _next_level(cls, current_level, ranking_system):
        levels = cls._sorted_levels(ranking_system)
        if not current_level:
            return None
        current_order = current_level.get("order", 0)
        for level in levels:
            if level.get("order", 0) > current_order:
                return level
        return None

    @classmethod
    def _is_keep_reached(cls, current_level_name, ranking_system, keep_account_level):
        if not keep_account_level:
            return False
        current_level = cls._find_level(current_level_name, ranking_system)
        keep_level = cls._find_level(keep_account_level, ranking_system)
        if current_level and keep_level:
            return current_level.get("order", 0) >= keep_level.get("order", 0)
        return str(current_level_name or "").strip().lower() == str(keep_account_level or "").strip().lower()

    @staticmethod
    def _normalize_ratio_for_ranking(value):
        text = str(value).strip().lower()
        if text in ["inf", "infinity", "∞"]:
            return 10000.0
        try:
            ratio = float(value)
            if math.isinf(ratio) or math.isnan(ratio):
                return 10000.0
            if ratio == 0 or ratio > 10000:
                return 10000.0
            return ratio
        except Exception:
            return 0.0

    def _requirement_progress(self, key, required_value, stats):
        required = self._to_float(required_value)
        if key == "weeks":
            join_at = self._parse_datetime(stats.get("join_at"))
            if join_at:
                current = max((datetime.now() - join_at).days / 7.0, 0)
            else:
                current = 0
            unit = "weeks"
            label = "Weeks"
        elif key == "download_gb":
            current = self._to_float(stats.get("download")) / (1024 ** 3)
            unit = "GiB"
            label = "Download"
        elif key == "ratio":
            current = self._normalize_ratio_for_ranking(stats.get("ratio"))
            unit = ""
            label = "Ratio"
        elif key == "bonus":
            current = self._to_float(stats.get("bonus"))
            unit = ""
            label = "Bonus"
        else:
            current = self._to_float(stats.get(key))
            unit = ""
            label = key

        if required <= 0:
            progress = 100.0
        else:
            progress = min(max(current / required, 0), 1.0) * 100

        need = max(required - current, 0)
        return {
            "key": key,
            "label": label,
            "current": round(current, 2),
            "required": round(required, 2),
            "progress": round(progress, 2),
            "met": progress >= 100,
            "need": round(need, 2),
            "unit": unit
        }

    @staticmethod
    def _overall(requirements):
        if not requirements:
            return 100.0
        return round(sum(item.get("progress", 0) for item in requirements) / len(requirements), 2)

    def build_status(self, site_stats):
        site_name = site_stats.get("site")
        current_level_name = site_stats.get("user_level")
        ranking_info = self.get_site_ranking_info(site_name=site_name, site_url=site_stats.get("url"))

        if not ranking_info:
            return {
                "configured": False,
                "site": site_name,
                "current_level": current_level_name,
                "next_level": None,
                "overall_progress": 0,
                "requirements": [],
                "level_steps": [],
                "keep_account_level": "",
                "current_is_keep": False,
                "rule_url": "",
                "is_special_level": False,
                "special_level_description": "",
                "status_type": "not_configured",
                "message": "站点未配置等级数据"
            }

        ranking_system = ranking_info.get("ranking_system") or {}
        keep_account_level = ranking_info.get("keep_account_level")
        rule_url = ranking_info.get("rule_url") or ""
        special_level = self._find_special_level(current_level_name, ranking_system)
        if special_level:
            return {
                "configured": True,
                "site": site_name,
                "current_level": current_level_name,
                "next_level": None,
                "overall_progress": 100,
                "requirements": [],
                "level_steps": self._build_level_steps(ranking_system, current_level_name, None, keep_account_level),
                "keep_account_level": keep_account_level or "",
                "current_is_keep": self._is_keep_reached(current_level_name, ranking_system, keep_account_level),
                "rule_url": rule_url,
                "is_special_level": True,
                "special_level_description": special_level.get("description", ""),
                "status_type": "special_level",
                "message": "特殊等级不参与晋升"
            }

        current_level = self._find_level(current_level_name, ranking_system)
        if not current_level:
            return {
                "configured": True,
                "site": site_name,
                "current_level": current_level_name,
                "next_level": None,
                "overall_progress": 0,
                "requirements": [],
                "level_steps": self._build_level_steps(ranking_system, current_level_name, None, keep_account_level),
                "keep_account_level": keep_account_level or "",
                "current_is_keep": self._is_keep_reached(current_level_name, ranking_system, keep_account_level),
                "rule_url": rule_url,
                "is_special_level": False,
                "special_level_description": "",
                "status_type": "mapping_error",
                "message": "当前等级未在映射中配置"
            }

        next_level = self._next_level(current_level, ranking_system)
        if not next_level:
            return {
                "configured": True,
                "site": site_name,
                "current_level": current_level_name,
                "next_level": None,
                "overall_progress": 100,
                "requirements": [],
                "level_steps": self._build_level_steps(ranking_system, current_level_name, None, keep_account_level),
                "keep_account_level": keep_account_level or "",
                "current_is_keep": self._is_keep_reached(current_level_name, ranking_system, keep_account_level),
                "rule_url": rule_url,
                "is_special_level": False,
                "special_level_description": "",
                "status_type": "highest_level",
                "message": "已达到最高等级"
            }

        requirements = []
        for key, required_value in (next_level.get("requirements") or {}).items():
            requirements.append(self._requirement_progress(key, required_value, site_stats))

        return {
            "configured": True,
            "site": site_name,
            "current_level": current_level_name,
            "next_level": next_level.get("name"),
            "overall_progress": self._overall(requirements),
            "requirements": requirements,
            "level_steps": self._build_level_steps(ranking_system, current_level_name, next_level.get("name"), keep_account_level),
            "keep_account_level": keep_account_level or "",
            "current_is_keep": self._is_keep_reached(current_level_name, ranking_system, keep_account_level),
            "rule_url": rule_url,
            "is_special_level": False,
            "special_level_description": "",
            "status_type": "normal",
            "message": ""
        }

