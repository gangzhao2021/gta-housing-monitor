"""Local owner gate for the full application; never use a URL as authority."""
import hashlib
import hmac
import os
import secrets

ITERATIONS = 600_000


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


def owner_gate(st):
    """Called before opening the private database or rendering any owner content."""
    verifier = os.environ.get("HOUSING_OWNER_VERIFIER")
    if not verifier:
        st.error("管理入口未配置身份验证，已拒绝访问。")
        st.stop()
    if st.session_state.get("owner_authenticated") is True:
        if st.button("退出管理端", key="owner-logout"):
            st.session_state.pop("owner_authenticated", None)
            st.rerun()
        return
    st.title("管理端登录")
    with st.form("owner-login"):
        password = st.text_input("管理密码", type="password")
        submitted = st.form_submit_button("登录")
    if submitted:
        if verify(password, verifier):
            st.session_state["owner_authenticated"] = True
            st.rerun()
        else:
            st.error("密码无效。")
    st.stop()
