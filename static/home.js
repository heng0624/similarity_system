// ========== AUTH FUNCTIONS ==========
function escapeHtml(text) {
    return text.replace(/&/g, "&amp;")
               .replace(/</g, "&lt;")
               .replace(/>/g, "&gt;");
}

function compareText() {
    const formData = new FormData();
    formData.append("user_text", document.getElementById("user_text").value);
    formData.append("compare_text", document.getElementById("compare_text").value);
    formData.append("mode", "TEXT");


    fetch("/similarity", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
     showResult(data);        // show preview

    if (data.preview_a && data.preview_b) {
        showDiff(data.preview_a, data.preview_b);  // <-- highlight differences here
    }
})

    .catch(err => console.error(err));
}
function compareURL() {
    const formData = new FormData();
    formData.append("user_url", document.getElementById("user_url").value);
    formData.append("compare_url", document.getElementById("compare_url").value);
    formData.append("mode", "URL");


    fetch("/similarity", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(showResult)
    .catch(err => console.error(err));
}
function compareFiles() {
    const formData = new FormData();

    const file1 = document.getElementById("file1").files[0];
    const file2 = document.getElementById("file2").files[0];
    const mode = document.getElementById("mode").value;

    if (file1) formData.append("file1", file1);
    if (file2) formData.append("file2", file2);
    formData.append("mode", mode);

    fetch("/similarity", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(showResult)
    .catch(err => console.error(err));
}

function showResult(data) {
    if (data.error) {
        alert(data.error);
        return;
    }
 
    document.getElementById("result").style.display = "block";
    document.getElementById("resMode").innerText = data.mode || "N/A";
    document.getElementById("resScore").innerText = data.score || 0;
    // 🔥 Add this to highlight differences
    if (data.preview_a && data.preview_b) {
        showDiff(data.preview_a, data.preview_b);
    }
}

document.getElementById("textBtn").addEventListener("click", compareText);
document.getElementById("urlBtn").addEventListener("click", compareURL);
document.getElementById("fileBtn").addEventListener("click", compareFiles);

function isValidEmail(email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
}


// ==================== MODAL FUNCTIONS ====================
function openModal(type) {
    document.getElementById("authModal").style.display = "block";
    switchForm(type);
}

function closeModal() {
    document.getElementById("authModal").style.display = "none";
}

function switchForm(type) {
    document.getElementById("loginForm").style.display = (type === "login") ? "block" : "none";
    document.getElementById("signupForm").style.display = (type === "signup") ? "block" : "none";
    document.getElementById("forgotForm").style.display = type === "forgot" ? "block" : "none";

}

// Close modal on outside click
window.onclick = function(event) {
    if (event.target === document.getElementById("authModal")) {
        closeModal();
    }
}



// ==================== HEADER UPDATE ====================
function updateHeaderUser() {
    const user = sessionStorage.getItem("loggedUser");
    const authButtons = document.getElementById("authButtons");
    const userDisplay = document.getElementById("userDisplay");
    const usernameText = document.getElementById("usernameText");

    if (!authButtons || !userDisplay) return;


    if (user) {
        authButtons.style.display = "none";
        userDisplay.style.display = "block";
        usernameText.innerText = user;
    } else {
        authButtons.style.display = "block";
        userDisplay.style.display = "none";
    }
}

// ==================== LOGOUT ====================
function logout() {
    sessionStorage.removeItem("loggedUser");
    window.location.href= "/home";
    showSuccess("Logged out successfully!", false); // no reload

}



   // ---------- LOGIN ----------
async function ajaxLogin() {
    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;

    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    const res = await fetch("/login", {
        method: "POST",
        body: formData
    });
    const data = await res.json();

    showSuccess(data.message); // display message
    if (data.status === "success") {
        closeModal(); // ✅ hide modal immediately
        // Optional: refresh header
        setTimeout(() => {
            location.reload();  // reload page to update username in navbar
        }, 600);
    }
     
}

//show password
function togglePassword(id) {
    const input = document.getElementById(id);

    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }
}

async function sendResetRequest() {
    const email = document.getElementById("forgotEmail").value;
    if (!email) {
        alert("Please enter your email");
        return;
    }

    const res = await fetch("/forgot_password", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"   // IMPORTANT
        },
        body: JSON.stringify({ email: email })
    });

    const data = await res.json();

    showSuccess(data.message, false);
}


// ---------- SIGNUP ----------
document.getElementById("signupButton").addEventListener("click", async () => {
    const username = document.getElementById("signupUsername").value;
    const email = document.getElementById("signupEmail").value;
    const password = document.getElementById("signupPassword").value;

    // console.log("Clicked signup!", username, email, password);

    if (!username || !email || !password) {
        alert("Please fill in all fields!");
        return;
    }

    const formData = new FormData();
    formData.append("username", username);
    formData.append("email", email);
    formData.append("password", password);

    const res = await fetch("/signup", { 
        method: "POST", 
        body: formData,
        credentials: "same-origin"  // <-- ensures cookies (sessions) are sent/received
    });
    const data = await res.json();

    showSuccess(data.message); // display message

     if (data.status === "success") {
        closeModal(); // ✅ hide modal immediately
        setTimeout(() => {
            location.reload();  // reload page to update username in navbar
        }, 600);
    }


});

async function updateProfile() {
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;

    try {
        const res = await fetch('/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email })
        });

        const data = await res.json(); // <--- parse response JSON

        if (data.status === 'success') {
            document.getElementById('usernameText').innerText = username; // update header
            showSuccess("Updated successfully!", false); // false = do not reload
        } else {
            showSuccess("Update failed: " + (data.message || "Unknown error"), false);
        }
    } catch (err) {
        console.error(err);
        showSuccess("Server error. Try again later.", false);
    }
}

// ==================== SUCCESS POPUP ====================
function showSuccess(msg, reload = true) {
    const box = document.getElementById("successMsg");
    box.innerText = msg;
    box.style.display = "block";
    box.style.opacity = 1;

    setTimeout(() => { box.style.opacity = 0; }, 1200);

    setTimeout(() => {
        box.style.display = "none";
        if (reload) location.reload();
    }, 1500);
}

async function loadHistory() {
    const res = await fetch("/api/history");
    const history = await res.json();

    const tbody = document.querySelector("#historyTable tbody");
    tbody.innerHTML = "";

    history.forEach((h, i) => {
        tbody.innerHTML += `
            <tr>
                <td>${i+1}</td>
                <td>${h.mode}</td>
                <td>${h.score}%</td>
                <td>${h.date}</td>
            </tr>
        `;
    });
}
loadHistory();

document.getElementById("file1").addEventListener("change", () => previewFile("file1", "file1Preview"));
document.getElementById("file2").addEventListener("change", () => previewFile("file2", "file2Preview"));

function previewFile(inputId, previewId) {
    const file = document.getElementById(inputId).files[0];
    const previewBox = document.getElementById(previewId);
    const previewContainer = document.getElementById("preview");

    if (!file) return;

    previewContainer.style.display = "block";
    previewBox.innerHTML = "<p>Loading...</p>";
    previewBox.style.overflow = "auto";
    previewBox.style.maxHeight = "480px";

    const reader = new FileReader();

    // ----------------------
    // IMAGE
    // ----------------------
    if (file.type.startsWith("image/")) {
        reader.onload = (e) => {
            previewBox.innerHTML = `<img src="${e.target.result}" style="max-width:100%;">`;
        };
        reader.readAsDataURL(file);
    }

    // ----------------------
    // PDF
    // ----------------------
    // ----------------------
// PDF (using object URL to support large files)
// ----------------------
else if (file.type === "application/pdf") {
    const pdfURL = URL.createObjectURL(file);
    previewBox.innerHTML = `
        <iframe 
            src="${pdfURL}" 
            style="width:100%; height:480px; border:none;">
        </iframe>
    `;
}


    // ----------------------
    // WORD (.docx)
    // ----------------------
    else if (file.name.endsWith(".docx")) {
        reader.onload = (e) => {
            mammoth.convertToHtml({ arrayBuffer: e.target.result })
                .then(result => {
                    previewBox.innerHTML = `<div>${result.value}</div>`;
                })
                .catch(() => {
                    previewBox.innerHTML = `<p>Unable to preview .docx file.</p>`;
                });
        };
        reader.readAsArrayBuffer(file);
    }

    // ----------------------
    // EXCEL (.xlsx / .xls)
    // ----------------------
    else if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
        reader.onload = (e) => {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            let html = '';
            workbook.SheetNames.forEach(sheetName => {
                const htmlstr = XLSX.utils.sheet_to_html(workbook.Sheets[sheetName]);
                html += `<h4>${sheetName}</h4>${htmlstr}`;
            });
            previewBox.innerHTML = html;
        };
        reader.readAsArrayBuffer(file);
    }

    // ----------------------
    // PPTX (.pptx)
    // ----------------------
    else if (file.name.endsWith(".pptx")) {
        previewBox.innerHTML = `<p>PPTX preview not fully supported. Consider converting to PDF first.</p>`;
    }

    // ----------------------
    // TEXT or CODE
    // ----------------------
    else if (file.type.startsWith("text/") || /\.(py|js|html|css|java|cpp|c|json|txt|md)$/i.test(file.name)) {
        reader.onload = (e) => {
            const code = escapeHtml(e.target.result);
            const lang = getLanguage(file.name);
            previewBox.innerHTML = `<pre><code class="language-${lang}">${code}</code></pre>`;
            Prism.highlightAll();
        };
        reader.readAsText(file);
    }

    // ----------------------
    // Unsupported
    // ----------------------
    else {
        previewBox.innerHTML = `<p>Preview not supported for this file type: ${file.name}</p>`;
    }
}

function escapeHtml(text) {
    return text.replace(/&/g, "&amp;")
               .replace(/</g, "&lt;")
               .replace(/>/g, "&gt;");
}

function getLanguage(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
        case 'py': return 'python';
        case 'js': return 'javascript';
        case 'java': return 'java';
        case 'cpp': return 'cpp';
        case 'c': return 'c';
        case 'html': return 'markup';
        case 'css': return 'css';
        case 'json': return 'json';
        case 'md': return 'markdown';
        default: return 'none';
    }
}
document.getElementById("highlightBtn").addEventListener("click", highlightDifferences);
function showDiff(textA, textB) {
    const linesA = textA.split("\n");
    const linesB = textB.split("\n");

    let diffHTML_A = "";
    let diffHTML_B = "";

    const maxLines = Math.max(linesA.length, linesB.length);

    for (let i = 0; i < maxLines; i++) {
        const a = linesA[i] || "";
        const b = linesB[i] || "";

        if (a === b) {
            diffHTML_A += `<div class="diff-green">${escapeHtml(a)}</div>`;
            diffHTML_B += `<div class="diff-green">${escapeHtml(b)}</div>`;
        } else {
            diffHTML_A += `<div class="diff-red">${escapeHtml(a)}</div>`;
            diffHTML_B += `<div class="diff-red">${escapeHtml(b)}</div>`;
        }
    }

    document.getElementById("diffA").innerHTML = diffHTML_A;
    document.getElementById("diffB").innerHTML = diffHTML_B;

    document.getElementById("diffContainer").style.display = "block";
}





document.getElementById("compareBtn").addEventListener("click", function () {
    const formData = new FormData();

    formData.append("user_text", document.getElementById("user_text").value);
    formData.append("compare_text", document.getElementById("compare_text").value);

    formData.append("user_url", document.getElementById("user_url").value);
    formData.append("compare_url", document.getElementById("compare_url").value);

    fetch("/similarity", {
        method: "POST",
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById("result_user").innerText = data.preview_a;
        document.getElementById("result_compare").innerText = data.preview_b;
        document.getElementById("score").innerText = "Similarity: " + data.score + "%";
    });
});
