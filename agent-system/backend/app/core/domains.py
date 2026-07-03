"""
领域配置模块（已迁移到 career_tracks.py）
此文件保留作为兼容层，所有功能委托到 app.core.career_tracks
"""

from app.core.career_tracks import (
    CareerTrackConfig,
    CAREER_TRACKS,
    DEFAULT_CAREER_TRACK,
    get_career_track,
    get_default_career_track,
    get_all_career_tracks,
    get_career_track_codes,
    get_career_track_from_input,
    build_career_prompt,
    # 兼容性别名
    get_domain_from_input,
    build_domain_prompt,
    get_default_domain,
    get_all_domains,
    get_domain_names,
)

# 向后兼容：保留 DomainConfig 别名
DomainConfig = CareerTrackConfig
DOMAINS = CAREER_TRACKS
DEFAULT_DOMAIN = DEFAULT_CAREER_TRACK

__all__ = [
    "CareerTrackConfig",
    "DomainConfig",
    "CAREER_TRACKS",
    "DOMAINS",
    "DEFAULT_CAREER_TRACK",
    "DEFAULT_DOMAIN",
    "get_career_track",
    "get_default_career_track",
    "get_all_career_tracks",
    "get_career_track_codes",
    "get_career_track_from_input",
    "build_career_prompt",
    "get_domain_from_input",
    "build_domain_prompt",
    "get_default_domain",
    "get_all_domains",
    "get_domain_names",
]
