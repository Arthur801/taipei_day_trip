function initializeUserDialog() {
  const memberButton = document.querySelector("#member-button");
  const signinDialog = document.querySelector(".dialog-signin");
  const signupDialog = document.querySelector(".dialog-signup");
  const signinForm = document.querySelector("#signin-form");
  const signupForm = document.querySelector("#signup-form");
  const signinMessage = document.querySelector("#signin-message");
  const signupMessage = document.querySelector("#signup-message");

  if (
    !memberButton || !signinDialog || !signupDialog
    || !signinForm || !signupForm || !signinMessage || !signupMessage
  ) return;

  const dialogs = [signinDialog, signupDialog];

  function setMessage(element, message = "", isSuccess = false) {
    element.textContent = message;
    element.hidden = !message;
    element.classList.toggle("is-success", isSuccess);
  }

  function clearMessages() {
    setMessage(signinMessage);
    setMessage(signupMessage);
  }

  function closeDialogs(restoreFocus = true) {
    dialogs.forEach((dialog) => {
      dialog.classList.remove("is-open");
      dialog.setAttribute("aria-hidden", "true");
    });
    document.body.style.overflow = "";
    if (restoreFocus) memberButton.focus();
  }

  function openDialog(dialog, firstInput) {
    closeDialogs(false);
    clearMessages();
    dialog.classList.add("is-open");
    dialog.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    firstInput.focus();
  }

  async function submitUserRequest(method, body) {
    const response = await fetch("/api/user", {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    return { response, data };
  }

  memberButton.addEventListener("click", () => {
    openDialog(signinDialog, signinForm.elements.email);
  });

  signinDialog.querySelector(".dialog-switch").addEventListener("click", () => {
    openDialog(signupDialog, signupForm.elements.name);
  });

  signupDialog.querySelector(".dialog-switch").addEventListener("click", () => {
    openDialog(signinDialog, signinForm.elements.email);
  });

  dialogs.forEach((dialog) => {
    dialog.querySelector(".dialog-close").addEventListener("click", () => closeDialogs());
    dialog.querySelector(".backdrop").addEventListener("click", () => closeDialogs());
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && dialogs.some((dialog) => dialog.classList.contains("is-open"))) {
      closeDialogs();
    }
  });

  signinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(signinMessage);
    const submitButton = signinForm.querySelector('[type="submit"]');
    submitButton.disabled = true;

    try {
      const { response, data } = await submitUserRequest("PUT", {
        email: signinForm.elements.email.value.trim(),
        password: signinForm.elements.password.value,
      });

      if (!response.ok || !data.token) {
        setMessage(signinMessage, data.message || "登入失敗，請確認 Email 和密碼");
        return;
      }

      try {
        localStorage.setItem("token", data.token);
      } catch (error) {
        console.error("Unable to save authentication token.", error);
        setMessage(signinMessage, "無法儲存登入狀態，請確認瀏覽器設定");
        return;
      }

      signinForm.reset();
      closeDialogs();
    } catch (error) {
      console.error("Unable to sign in.", error);
      setMessage(signinMessage, "連線失敗，請稍後再試");
    } finally {
      submitButton.disabled = false;
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(signupMessage);
    const submitButton = signupForm.querySelector('[type="submit"]');
    submitButton.disabled = true;

    try {
      const { response, data } = await submitUserRequest("POST", {
        name: signupForm.elements.name.value.trim(),
        email: signupForm.elements.email.value.trim(),
        password: signupForm.elements.password.value,
      });

      if (!response.ok || !data.ok) {
        setMessage(signupMessage, data.message || "註冊失敗，請檢查輸入資料");
        return;
      }

      signupForm.reset();
      setMessage(signupMessage, "註冊成功，請登入系統", true);
    } catch (error) {
      console.error("Unable to sign up.", error);
      setMessage(signupMessage, "連線失敗，請稍後再試");
    } finally {
      submitButton.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", initializeUserDialog);
