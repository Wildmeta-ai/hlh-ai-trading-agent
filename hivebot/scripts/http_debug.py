# scripts/http_debug.py
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

if hasattr(WebAssistantsFactory, "_rest_assistant") and hasattr(WebAssistantsFactory._rest_assistant, "execute_request"):
    _old_exec = WebAssistantsFactory._rest_assistant.execute_request

    async def _verbose_exec(self, url, *args, data=None, **kwargs):
        try:
            # 只打印 Hyperliquid 的 /info 调用，避免刷屏
            if "hyperliquid" in url and url.endswith("/info"):
                print("\n==== HL /info REQUEST ====")
                print("URL :", url)
                print("DATA:", data)   # 这里就是发送给 /info 的 JSON
                print("=========================\n")
        except Exception:
            pass
        return await _old_exec(self, url, *args, data=data, **kwargs)

    WebAssistantsFactory._rest_assistant.execute_request = _verbose_exec
    print("[http_debug] Patched WebAssistantsFactory._rest_assistant.execute_request")
else:
    print("[http_debug] Could not patch: structure not found (HBOT version mismatch?)")
