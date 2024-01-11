console.log(hallpageContext.order);

newestBtnLabel = document.getElementById("newestBtnLabel");
newestBtn = document.getElementById("newestBtn");
popBtnLabel = document.getElementById("popBtnLabel");
popBtn = document.getElementById("popBtn");

if (hallpageContext.order=="0") {
	newestBtnLabel.classList.add("active");
	newestBtn.checked = true;
}
else if (hallpageContext.order=="1") {
	popBtnLabel.classList.add("active");
	popBtn.checked = true;
}