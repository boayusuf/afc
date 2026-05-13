"""AFC system implementations."""

from . import (
    system_a_gpt4o,
    system_b_tavily_rag,
    system_c_google_fc,
    system_d_filtered_rag,
    system_e_llama,
)
from .base import Verdict, SYSTEM_REGISTRY

ALL_SYSTEMS = {
    "A": system_a_gpt4o.run,
    "B": system_b_tavily_rag.run,
    "C": system_c_google_fc.run,
    "D": system_d_filtered_rag.run,
    "E": system_e_llama.run,
}
