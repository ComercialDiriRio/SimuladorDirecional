let currentImageIndex = 0;
let currentImages = [];

function openGallery(imagesJson, index) {
    currentImages = JSON.parse(imagesJson);
    currentImageIndex = index;
    showImage(currentImageIndex);
    document.getElementById("myModal").style.display = "block";
}

function closeModal() {
    document.getElementById("myModal").style.display = "none";
}

function plusSlides(n) {
    currentImageIndex += n;
    if (currentImageIndex >= currentImages.length) {
        currentImageIndex = 0;
    }
    if (currentImageIndex < 0) {
        currentImageIndex = currentImages.length - 1;
    }
    showImage(currentImageIndex);
}

function showImage(index) {
    var modalImg = document.getElementById("img01");
    modalImg.src = currentImages[index];
}

document.addEventListener('keydown', function(event) {
    if(document.getElementById("myModal").style.display === "block"){
        if(event.key === "ArrowLeft") {
            plusSlides(-1);
        }
        else if(event.key === "ArrowRight") {
            plusSlides(1);
        }
        else if(event.key === "Escape") {
            closeModal();
        }
    }
});

window.onclick = function(event) {
  var modal = document.getElementById("myModal");
  if (event.target == modal) {
    modal.style.display = "none";
  }
};
