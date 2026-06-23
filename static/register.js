document.getElementById("registerForm").addEventListener("submit", function(e){

    const password = document.getElementById("password").value;
    const button = document.querySelector(".register-btn");

    if(password.length < 6){
        e.preventDefault();
        alert("Пароль повинен містити мінімум 6 символів");
        return;
    }

    button.classList.add("loading");
});

function togglePassword(){
    const passwordInput = document.getElementById("password");

    if(passwordInput.type === "password"){
        passwordInput.type = "text";
    } else {
        passwordInput.type = "password";
    }
}