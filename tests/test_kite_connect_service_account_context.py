from src.services.kite_connect_service import KiteConnectService


def _make_service():
    service = object.__new__(KiteConnectService)
    service._active_session = None
    return service


def test_resolve_account_context_uses_zerodha_user_id_when_present(monkeypatch):
    monkeypatch.delenv("PAPER_TRADING_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("ZERODHA_ACCOUNT_ID", raising=False)
    monkeypatch.setenv("ZERODHA_USER_ID", "WH6407")

    service = _make_service()

    assert service._resolve_account_context() == "WH6407"


def test_resolve_account_context_prefers_explicit_account_id(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_ACCOUNT_ID", "paper-account")
    monkeypatch.setenv("ZERODHA_ACCOUNT_ID", "zerodha-account")
    monkeypatch.setenv("ZERODHA_USER_ID", "WH6407")

    service = _make_service()

    assert service._resolve_account_context() == "paper-account"
