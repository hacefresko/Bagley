var itemClassName = "carousel-slide";
var items = document.getElementsByClassName(itemClassName),
	totalItems = items.length,
	slide = 0,
	moving = true;
var slideControls;

function setAnimation(slide) {
	items[slide].firstElementChild.classList.add('animated');
}

function setInitialClasses() {
	items[items.length - 1].classList.add("prev");
	items[0].classList.add("active");
	items[1].classList.add("next");
	setAnimation(slide);
}

function setEventListeners() {
	var next = document.getElementsByClassName("carousel__button--next")[0],
		prev = document.getElementsByClassName("carousel__button--prev")[0];
	next.addEventListener("click", moveNext);
	prev.addEventListener("click", movePrev);
}

function moveNext() {
	if (!moving) {
		if (slide === items.length - 1) {
			slide = 0;
		} else {
			slide++;
		}
		newActiveDots(slide);
		moveCarouselTo(slide);
	}
}

function movePrev() {
	if (!moving) {
		if (slide === 0) {
			slide = items.length - 1;
		} else {
			slide--;
		}
		newActiveDots(slide);
		moveCarouselTo(slide);
	}
}

function disableInteraction() {
	moving = true;

	setTimeout(function () {
		moving = false;
	}, 500);
}

function moveCarouselTo(slide) {
	if (!moving) {
		disableInteraction();
		setAnimation(slide);

		var newPrevious = slide - 1,
			newNext = slide + 1,

			// The next two (oldPrevious and oldNext) should be added to and subtracted by the amount of slides it takes to get to them
			// So if there are three slides... it should be 1...if it is 4 slides it should be 2 -- I really have NO idea why this functions the way it does
			// This is something left over from Nikita's code. The saga continues...if it's 5 it's also 2...so perhaps it's 2 for anything above 3 -- i have no idea.
			oldPrevious = slide - 1,
			oldNext = slide + 1;

		if (items.length > 1) {
			if (newPrevious <= 0) {
				oldPrevious = items.length - 1;
			} else if (newNext >= items.length - 1) {
				oldNext = 0;
			}

			if (slide === 0) {
				newPrevious = items.length - 1;

				// Again...for oldPrevious here...for some reason we have to do the same math as above...so this number needs to change based on the number of slides.
				oldPrevious = items.length - 1;

				oldNext = slide + 1;
			} else if (slide === items.length - 1) {
				newPrevious = slide - 1;
				newNext = 0;
				oldNext = 1;
			}

			items[oldPrevious].className = itemClassName;
			items[oldNext].className = itemClassName;

			items[newPrevious].className = itemClassName + " prev";
			items[slide].className = itemClassName + " active";
			items[newNext].className = itemClassName + " next";
		}
	}
}

// function initAnimationSlide(slide) {
// 	var sildeImages = items[slide].querySelectorAll("img");
// 	var imageCount = sildeImages.length;
// 	var imagesLoaded = 0;

// 	for (var i = 0; i < imageCount; i++) {
// 		sildeImages[i].onload = function () {
// 			imagesLoaded++;
// 			if (imagesLoaded == imageCount) {
// 				setAnimation(slide);
// 			}
// 		};
// 	}
// }

function newActiveDots(newIndex) {
	for (var i = 0; i < slideControls.length; i++) {
		if (i === newIndex) {
			slideControls[i].classList.add("slick-active");
		} else {
			slideControls[i].classList = null;
		}
	}
}

function initCarouselControls() {
	slideControls = document.querySelectorAll(".hp-header-carousel .slick-dots li");
	slideControls[0].classList.add("slick-active");

	for (var i = 0; i < slideControls.length; i++) {
		slideControls[i].addEventListener("click", function () {
			slide = this.dataset.slidenumber - 1;
			newActiveDots(slide);
			moveCarouselTo(slide);
		});
	}
}

function initCarousel() {
	if (document.querySelector(".carousel-wrapper")) {
		setInitialClasses();
		initCarouselControls();
		setEventListeners();
		moving = false;
	} else {
		setTimeout(initCarousel, 50);
	}
}

initCarousel();
