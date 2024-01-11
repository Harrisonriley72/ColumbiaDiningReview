newestBtnLabel = document.getElementById("newestBtnLabel");
newestBtn = document.getElementById("newestBtn");
popBtnLabel = document.getElementById("popBtnLabel");
popBtn = document.getElementById("popBtn");

if (context.order=="0") {
	newestBtnLabel.classList.add("active");
	newestBtn.checked = true;
}
else if (context.order=="1") {
	popBtnLabel.classList.add("active");
	popBtn.checked = true;
}