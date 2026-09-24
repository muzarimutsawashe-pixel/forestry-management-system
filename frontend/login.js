const API_URL = "https://forestry-backend-vlyr.onrender.com/";
const LOGIN_TIMEOUT = 8000;
const SESSION_TIMEOUT_MS = 30 * 60 * 1000;   // 30 minutes idle


/* ============================================================
   INITIALISE
============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    // Show a message if the user was bounced here by a timeout
    const params = new URLSearchParams(window.location.search);
    if (params.get("reason") === "timeout") {
        const el = document.getElementById("errorMessage");
        if (el) {
            el.textContent = "Your session expired due to inactivity. Please log in again.";
            el.style.display = "block";
        }
    }

    const form = document.getElementById("loginForm");
    if (!form) return;

    setupLogin();

});


/* ============================================================
   LOGIN SETUP
============================================================ */

function setupLogin() {

    const form = document.getElementById("loginForm");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");

    if (togglePassword && passwordInput) {
        togglePassword.addEventListener("click", function () {
            if (passwordInput.type === "password") {
                passwordInput.type = "text";
                togglePassword.textContent = "Hide";
            } else {
                passwordInput.type = "password";
                togglePassword.textContent = "Show";
            }
        });
    }

    form.addEventListener("submit", handleLogin);
}


/* ============================================================
   LOGIN
============================================================ */

async function handleLogin(event) {

    event.preventDefault();

    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    const username = usernameInput ? usernameInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";

    if (!username) {
        showMessage("Please enter your username.", "error");
        return;
    }

    if (!password) {
        showMessage("Please enter your password.", "error");
        return;
    }

    const button = document.getElementById("loginButton");
    const buttonText = document.getElementById("loginButtonText");

    if (button) button.disabled = true;
    if (buttonText) buttonText.textContent = "SIGNING IN...";

    clearMessage();

    try {

        console.log("Connecting to:", `${API_URL}/api/login`);

        const response = await fetchWithTimeout(
            `${API_URL}/api/login`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    username: username,
                    password: password,
                }),
            },
            LOGIN_TIMEOUT
        );

        console.log("Login HTTP status:", response.status);

        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            throw new Error("The server returned an invalid response.");
        }

        console.log("Login server response:", data);

        if (!response.ok) {
            throw new Error(
                data.detail || data.message || "Invalid username or password."
            );
        }

        if (!data.token) {
            throw new Error("Login succeeded but the server did not return a token.");
        }

        /* ---------- Save session ---------- */

        localStorage.setItem("token",       data.token);
        localStorage.setItem("username",    data.username || username);
        localStorage.setItem("role",        data.role || "forester");
        localStorage.setItem("estate_id",   data.estate_id != null ? data.estate_id : "");
        localStorage.setItem("loggedIn",    "true");
        localStorage.setItem("lastActivity", Date.now().toString());

        // Optional alias for any code that expects access_token
        localStorage.setItem("access_token", data.token);

        showMessage("Login successful. Opening dashboard...", "success");

        setTimeout(function () {
            window.location.replace("index.html");
        }, 500);

    } catch (error) {

        console.error("Login error:", error);

        showMessage(
            error.message || "Unable to connect to the server.",
            "error"
        );

        if (button) button.disabled = false;
        if (buttonText) buttonText.textContent = "SIGN IN";

    }
}


/* ============================================================
   FETCH WITH TIMEOUT
============================================================ */

async function fetchWithTimeout(url, options, timeout) {

    const controller = new AbortController();

    const timeoutId = setTimeout(function () {
        controller.abort();
    }, timeout);

    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);

        if (error.name === "AbortError") {
            throw new Error("Request timed out. Please try again.");
        }
        throw error;
    }
}


/* ============================================================
   MESSAGE
============================================================ */

function showMessage(text, type) {

    const element = document.getElementById("loginMessage");

    if (!element) {
        // Fall back to the error box if loginMessage is not present
        const err = document.getElementById("errorMessage");
        if (err) {
            err.textContent = text;
            err.style.display = "block";
        }
        return;
    }

    element.textContent = text;
    element.className = "login-message";
    if (type) element.classList.add(type);
}


function clearMessage() {
    const element = document.getElementById("loginMessage");
    if (!element) return;
    element.textContent = "";
    element.className = "login-message";
}