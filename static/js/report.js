
document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       GEOLOCALISATION
    ===================================================== */

    const locationButton = document.getElementById("locationButton");
    const locationStatus = document.getElementById("locationStatus");


    locationButton.addEventListener("click", function () {

        if (!navigator.geolocation) {

            locationStatus.textContent =
                "La géolocalisation n'est pas supportée par votre navigateur.";

            return;
        }


        locationStatus.innerHTML = `
            <i class="bi bi-arrow-repeat"></i>
            Recherche de votre position...
        `;


        navigator.geolocation.getCurrentPosition(

            function (position) {

                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                document.getElementById("latitude").value = latitude;
                document.getElementById("longitude").value = longitude;



                locationStatus.innerHTML = `
                    <i class="bi bi-check-circle-fill"></i>
                    Position récupérée avec succès.
                `;


                console.log("Latitude :", latitude);
                console.log("Longitude :", longitude);


                /*
                Nous allons ensuite envoyer ces coordonnées
                vers Flask.
                */

            },


            function () {

                locationStatus.innerHTML = `
                    <i class="bi bi-x-circle-fill"></i>
                    Impossible de récupérer votre position.
                    Vérifiez que vous avez autorisé la géolocalisation.
                `;

            }

        );

    });



    /* =====================================================
       APERÇU IMAGE
    ===================================================== */

    const imageUpload =
        document.getElementById("imageUpload");


    const imagePreview =
        document.getElementById("imagePreview");


    const imagePreviewContainer =
        document.getElementById("imagePreviewContainer");


    const removeImage =
        document.getElementById("removeImage");


    imageUpload.addEventListener("change", function () {

        const file = this.files[0];


        if (!file) {

            return;

        }


        /* Vérification que le fichier est une image */

        if (!file.type.startsWith("image/")) {

            alert(
                "Veuillez sélectionner une image valide."
            );

            imageUpload.value = "";

            return;

        }


        const reader = new FileReader();


        reader.onload = function (event) {

            imagePreview.src =
                event.target.result;


            imagePreviewContainer.classList.add(
                "active"
            );

        };


        reader.readAsDataURL(file);

    });



    /* =====================================================
       SUPPRESSION IMAGE
    ===================================================== */

    removeImage.addEventListener("click", function () {

        imageUpload.value = "";

        imagePreview.src = "";

        imagePreviewContainer.classList.remove(
            "active"
        );

    });



    /* =====================================================
       SOUMISSION FORMULAIRE
    ===================================================== */

    const reportForm =
        document.querySelector(".report-form");


    reportForm.addEventListener("submit", function () {

        const submitButton =
            document.querySelector(".submit-button");


        submitButton.disabled = true;


        submitButton.innerHTML = `

            <span class="spinner-border spinner-border-sm"
                role="status">

            </span>

            Envoi du signalement...

        `;

    });

});

