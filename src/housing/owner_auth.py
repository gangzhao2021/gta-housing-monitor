"""Local password gate shared by the management and read-only display apps."""
import hashlib
import hmac
import os
import secrets
import time

ITERATIONS = 600_000
SESSION_SECONDS = 3600


def make_verifier(password, *, salt=None):
    if not password:
        raise ValueError("Owner password must not be empty")
    salt = salt or secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify(password, verifier):
    try:
        method, rounds, salt, expected = verifier.split("$")
        if method != "pbkdf2_sha256" or int(rounds) < ITERATIONS:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def session_valid(state, verifier, *, now=None):
    now = time.time() if now is None else now
    stamp = state.get("owner_authenticated_at")
    expected = hashlib.sha256(verifier.encode("utf-8")).hexdigest()
    return (state.get("owner_authenticated") is True
            and state.get("owner_verifier_fingerprint") == expected
            and isinstance(stamp, (int, float)) and 0 <= now - stamp < SESSION_SECONDS)


def owner_gate(st, *, title="管理端登录", logout_label="退出管理端"):
    """Called before opening the private database or rendering any owner content."""
    verifier = os.environ.get("HOUSING_OWNER_VERIFIER")
    if not verifier:
        st.error("本机密码尚未设置，已拒绝访问。请先按使用指南设置密码，再重启此页面。")
        st.stop()
    if session_valid(st.session_state, verifier):
        if st.button(logout_label, key="owner-logout"):
            st.session_state.pop("owner_authenticated", None)
            st.session_state.pop("owner_authenticated_at", None)
            st.session_state.pop("owner_verifier_fingerprint", None)
            st.rerun()
        return
    st.session_state.pop("owner_authenticated", None)
    st.title(title)
    with st.form("owner-login"):
        password = st.text_input("管理密码", type="password")
        submitted = st.form_submit_button("登录")
    if submitted:
        if verify(password, verifier):
            st.session_state["owner_authenticated"] = True
            st.session_state["owner_authenticated_at"] = time.time()
            st.session_state["owner_verifier_fingerprint"] = hashlib.sha256(verifier.encode("utf-8")).hexdigest()
            st.rerun()
        else:
            st.error("密码无效。")
    st.stop()
