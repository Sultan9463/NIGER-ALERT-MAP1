const logoutAt = document.body.dataset.logoutAt;

if (logoutAt) {

    const logoutTime =
        new Date(logoutAt).getTime();

    const now =
        Date.now();

    const remaining =
        logoutTime - now;


    if (remaining <= 0) {

        window.location.href =
            "/auto-logout";

    } else {

        setTimeout(() => {

            window.location.href =
                "/auto-logout";

        }, remaining);

    }

}