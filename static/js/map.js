document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       INITIALISATION DE LA CARTE
    ===================================================== */

    const map = L.map("map").setView(
        [17.6078, 8.0817],
        5.5
    );


    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution:
                '&copy; OpenStreetMap contributors'
        }
    ).addTo(map);


    /* =====================================================
       ELEMENTS HTML
    ===================================================== */

    const typeFilter =
        document.getElementById("typeFilter");

    const riskFilter =
        document.getElementById("riskFilter");

    const resetButton =
        document.getElementById("resetMapFilters");

    const locateButton =
        document.getElementById("locateUser");

    const refreshButton =
        document.getElementById("refreshMap");

    const visibleReports =
        document.getElementById("visibleReports");

    const userCoordinates =
        document.getElementById("userCoordinates");

    const mapLoading =
        document.getElementById("mapLoading");


    /* =====================================================
       STOCKAGE DES MARQUEURS
    ===================================================== */

    let markers = [];

    let userMarker = null;


    /* =====================================================
       VERIFICATION DES DONNEES
    ===================================================== */

    console.log(
        "Signalements reçus :",
        reports
    );


    /* =====================================================
       CREER LES OPTIONS DU FILTRE TYPE
    ===================================================== */

    function populateTypeFilter() {

        if (!typeFilter) {
            return;
        }

        const types = [];

        reports.forEach(function (report) {

            if (
                report.incident_type &&
                !types.includes(report.incident_type)
            ) {

                types.push(
                    report.incident_type
                );

            }

        });


        types.sort();


        types.forEach(function (type) {

            const option =
                document.createElement("option");

            option.value = type;

            option.textContent = type;

            typeFilter.appendChild(option);

        });

    }


    /* =====================================================
       DETERMINER LA COULEUR SELON L'URGENCE
    ===================================================== */

    function getMarkerColor(urgency) {

        const value =
            String(urgency || "")
                .toLowerCase()
                .trim();


        /*
         * RISQUE ELEVE
         */

        if (
            value === "danger" ||
            value === "élevé" ||
            value === "eleve" ||
            value === "urgent" ||
            value === "haute" ||
            value === "haut"
        ) {

            return "#dc3545";

        }


        /*
         * RISQUE MOYEN
         */

        if (
            value === "warning" ||
            value === "moyen" ||
            value === "moyenne" ||
            value === "modéré" ||
            value === "modere"
        ) {

            return "#fd7e14";

        }


        /*
         * RISQUE FAIBLE
         */

        if (
            value === "safe" ||
            value === "faible" ||
            value === "basse" ||
            value === "bas"
        ) {

            return "#198754";

        }


        /*
         * VALEUR PAR DEFAUT
         */

        return "#0d6efd";

    }


    /* =====================================================
       NOM DE L'URGENCE
    ===================================================== */

    function getUrgencyLabel(urgency) {

        const value =
            String(urgency || "")
                .toLowerCase()
                .trim();


        if (
            value === "danger" ||
            value === "élevé" ||
            value === "eleve" ||
            value === "urgent" ||
            value === "haute" ||
            value === "haut"
        ) {

            return "Risque élevé";

        }


        if (
            value === "warning" ||
            value === "moyen" ||
            value === "moyenne" ||
            value === "modéré" ||
            value === "modere"
        ) {

            return "Risque moyen";

        }


        if (
            value === "safe" ||
            value === "faible" ||
            value === "basse" ||
            value === "bas"
        ) {

            return "Risque faible";

        }


        return urgency || "Non défini";

    }


    /* =====================================================
       COULEUR DU BADGE D'URGENCE
    ===================================================== */

    function getUrgencyBadge(urgency) {

        const color =
            getMarkerColor(urgency);

        const label =
            getUrgencyLabel(urgency);


        return `
            <span
                style="
                    display:inline-block;
                    background:${color};
                    color:white;
                    padding:4px 9px;
                    border-radius:20px;
                    font-size:12px;
                    font-weight:600;
                "
            >
                ${label}
            </span>
        `;

    }


    /* =====================================================
       COULEUR DU STATUT
    ===================================================== */

    function getStatusBadge(status) {

        const value =
            String(status || "")
                .toLowerCase()
                .trim();


        let background = "#6c757d";


        if (value === "en attente") {

            background = "#6c757d";

        }


        if (value === "en cours") {

            background = "#0d6efd";

        }


        if (
            value === "traite" ||
            value === "traité"
        ) {

            background = "#198754";

        }


        return `
            <span
                style="
                    display:inline-block;
                    background:${background};
                    color:white;
                    padding:4px 9px;
                    border-radius:20px;
                    font-size:12px;
                    font-weight:600;
                "
            >
                ${status || "Non défini"}
            </span>
        `;

    }


    /* =====================================================
       CREER UN MARQUEUR
    ===================================================== */

    function createMarker(report) {

        const latitude =
            parseFloat(report.latitude);

        const longitude =
            parseFloat(report.longitude);


        /*
         * Vérifier les coordonnées
         */

        if (
            Number.isNaN(latitude) ||
            Number.isNaN(longitude)
        ) {

            return null;

        }


        /*
         * Vérifier que les coordonnées
         * sont géographiquement plausibles
         */

        if (
            latitude < -90 ||
            latitude > 90 ||
            longitude < -180 ||
            longitude > 180
        ) {

            return null;

        }


        /*
         * Couleur
         */

        const color =
            getMarkerColor(report.urgency);


        /* =================================================
           ICONE PERSONNALISEE
        ================================================= */

        const markerIcon =
            L.divIcon({

                className:
                    "niger-alert-marker",

                html: `
                    <div
                        style="
                            width:20px;
                            height:20px;
                            background:${color};
                            border:3px solid white;
                            border-radius:50%;
                            box-shadow:
                                0 2px 8px rgba(0,0,0,.35);
                        "
                    ></div>
                `,

                iconSize: [
                    20,
                    20
                ],

                iconAnchor: [
                    10,
                    10
                ],

                popupAnchor: [
                    0,
                    -10
                ]

            });


        /*
         * Création du marqueur
         */

        const marker =
            L.marker(
                [
                    latitude,
                    longitude
                ],
                {
                    icon: markerIcon
                }
            );


        /* =================================================
           IMAGE
        ================================================= */

        let imageHTML = "";


        if (report.image) {

            imageHTML = `
                <img
                    src="/static/uploads/${report.image}"
                    alt="Image du signalement"
                    style="
                        width:100%;
                        height:150px;
                        object-fit:cover;
                        border-radius:10px;
                        margin-bottom:12px;
                        display:block;
                    "
                >
            `;

        }


        /* =================================================
           ADRESSE
        ================================================= */

        let addressHTML = "";


        if (report.address) {

            addressHTML = `
                <div
                    style="
                        margin-bottom:8px;
                        font-size:13px;
                    "
                >
                    <strong>
                        <i class="bi bi-geo-alt"></i>
                        Adresse :
                    </strong>

                    ${report.address}
                </div>
            `;

        }


        /* =================================================
           POPUP
        ================================================= */

        marker.bindPopup(

            `
            <div
                style="
                    width:270px;
                    font-family:Arial,sans-serif;
                "
            >

                ${imageHTML}


                <h5
                    style="
                        margin:0 0 12px;
                        font-weight:700;
                        color:#172033;
                    "
                >
                    ${report.title}
                </h5>


                <div
                    style="
                        margin-bottom:8px;
                        font-size:13px;
                    "
                >

                    <strong>
                        Type :
                    </strong>

                    ${report.incident_type}

                </div>


                <div
                    style="
                        margin-bottom:8px;
                        font-size:13px;
                    "
                >

                    <strong>
                        Localisation :
                    </strong>

                    ${report.city},
                    ${report.region}

                </div>


                ${addressHTML}


                <div
                    style="
                        margin-bottom:10px;
                    "
                >

                    ${getUrgencyBadge(
                report.urgency
            )}

                    ${getStatusBadge(
                report.status
            )}

                </div>


                <hr>


                <p
                    style="
                        font-size:13px;
                        line-height:1.5;
                        margin:0;
                        color:#555;
                    "
                >

                    ${report.description}

                </p>


            </div>
            `

        );


        return marker;

    }


    /* =====================================================
       AFFICHER LES SIGNALEMENTS
    ===================================================== */

    function displayReports() {

        /* =================================================
           SUPPRIMER LES ANCIENS MARQUEURS
        ================================================= */

        markers.forEach(function (marker) {

            map.removeLayer(marker);

        });

        markers = [];


        /* =================================================
           RECUPERER LES FILTRES
        ================================================= */

        const selectedType =
            typeFilter
                ? typeFilter.value
                : "all";


        const selectedRisk =
            riskFilter
                ? riskFilter.value
                : "all";


        console.log(
            "Type sélectionné :",
            selectedType
        );


        console.log(
            "Risque sélectionné :",
            selectedRisk
        );


        /* =================================================
           FILTRAGE
        ================================================= */

        const filteredReports =
            reports.filter(function (report) {


                /* -----------------------------------------
                   FILTRE TYPE
                ----------------------------------------- */

                let typeMatch = true;


                if (
                    selectedType !== "all"
                ) {

                    typeMatch =
                        String(
                            report.incident_type || ""
                        )
                            .trim()
                            .toLowerCase()
                        ===
                        String(
                            selectedType
                        )
                            .trim()
                            .toLowerCase();

                }


                /* -----------------------------------------
                   FILTRE RISQUE
                ----------------------------------------- */

                let riskMatch = true;


                if (
                    selectedRisk !== "all"
                ) {

                    const reportUrgency =
                        String(
                            report.urgency || ""
                        )
                            .trim()
                            .toLowerCase();


                    const selectedUrgency =
                        String(
                            selectedRisk
                        )
                            .trim()
                            .toLowerCase();


                    riskMatch =
                        reportUrgency
                        ===
                        selectedUrgency;

                }


                /* -----------------------------------------
                   RESULTAT
                ----------------------------------------- */

                return (
                    typeMatch &&
                    riskMatch
                );

            });


        /* =================================================
           AFFICHER LES MARQUEURS
        ================================================= */

        filteredReports.forEach(
            function (report) {

                const marker =
                    createMarker(report);


                if (marker) {

                    marker.addTo(map);

                    markers.push(marker);

                }

            }
        );


        /* =================================================
           METTRE A JOUR LE COMPTEUR
        ================================================= */

        if (visibleReports) {

            visibleReports.textContent =
                markers.length;

        }


        /* =================================================
           MESSAGE CONSOLE
        ================================================= */

        console.log(
            "Signalements affichés :",
            filteredReports.length
        );

    }


    /* =====================================================
       FILTRE TYPE
    ===================================================== */

    if (typeFilter) {

        typeFilter.addEventListener(
            "change",
            function () {

                displayReports();

            }
        );

    }


    if (riskFilter) {

        riskFilter.addEventListener(
            "change",
            function () {

                displayReports();

            }
        );

    }

    /* =====================================================
       FILTRE RISQUE
    ===================================================== */

    if (riskFilter) {

        riskFilter.addEventListener(
            "change",
            displayReports
        );

    }


    /* =====================================================
       RESET
    ===================================================== */

  if (resetButton) {

    resetButton.addEventListener(
        "click",
        function () {

            if (typeFilter) {

                typeFilter.value =
                    "all";

            }


            if (riskFilter) {

                riskFilter.value =
                    "all";

            }


            displayReports();

        }
    );

}


    /* =====================================================
       LOCALISATION UTILISATEUR
    ===================================================== */

    if (locateButton) {

        locateButton.addEventListener(
            "click",
            function () {

                if (!navigator.geolocation) {

                    alert(
                        "La géolocalisation n'est pas supportée par votre navigateur."
                    );

                    return;

                }


                locateButton.disabled =
                    true;


                navigator.geolocation.getCurrentPosition(

                    function (position) {

                        const latitude =
                            position.coords.latitude;

                        const longitude =
                            position.coords.longitude;


                        /*
                         * Centrer la carte
                         */

                        map.setView(
                            [
                                latitude,
                                longitude
                            ],
                            15
                        );


                        /*
                         * Supprimer l'ancien
                         * marqueur utilisateur
                         */

                        if (userMarker) {

                            map.removeLayer(
                                userMarker
                            );

                        }


                        /*
                         * Marqueur utilisateur
                         */

                        userMarker =
                            L.circleMarker(
                                [
                                    latitude,
                                    longitude
                                ],
                                {
                                    radius: 9,
                                    weight: 3
                                }
                            );


                        userMarker
                            .addTo(map)
                            .bindPopup(
                                "📍 Vous êtes ici"
                            )
                            .openPopup();


                        /*
                         * Afficher coordonnées
                         */

                        if (
                            userCoordinates
                        ) {

                            userCoordinates.textContent =
                                `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;

                        }


                        locateButton.disabled =
                            false;

                    },


                    function () {

                        alert(
                            "Impossible de récupérer votre position. Vérifiez l'autorisation de géolocalisation."
                        );


                        locateButton.disabled =
                            false;

                    },


                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }

                );

            }
        );

    }


    /* =====================================================
       ACTUALISER LA CARTE
    ===================================================== */

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            function () {

                displayReports();

                map.invalidateSize();

            }
        );

    }


    /* =====================================================
       INITIALISATION
    ===================================================== */

    populateTypeFilter();

    displayReports();


    /* =====================================================
       MASQUER LE CHARGEMENT
    ===================================================== */

    setTimeout(
        function () {

            if (mapLoading) {

                mapLoading.style.display =
                    "none";

            }

        },
        700
    );

});