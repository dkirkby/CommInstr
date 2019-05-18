$(document).ready(function() {
    initialize();
});

function initialize() {
    console.log("Initialize");
}

var merged;

function initnights(data) {
    merged = data;
    var nightlist = $("#nightlist");
    // Use reverse lexical sort order.
    nights = Object.keys(merged).sort().reverse();
    $.each(nights, function(idx, night) {
        var exposures = merged[night];
        console.log("night " + night + " has " + exposures.length + " exposures.");
        var link = $("<a/>", {"class": "mdl-navigation__link", "href":"#", "html": night});
        link.click(function() {
            $(".mdl-navigation__link").removeClass("selected");
            $(this).addClass("selected");
            loadnight(night)
        });
        link.appendTo(nightlist);
    });
}

function loadnight(night) {
    // Remove images from any previous night.
    var parent = $("#content");
    parent.empty();
    parent.scrollTop();
    // Add a header with a link to the night summary.
    var summary = "http://desi-www.kpno.noao.edu:8090/nightsum/nightsum-" +
        night.substr(0, 4) + "-" + night.substr(4, 2) + "-" + night.substr(6, 2) + "/nightsum.html";
    parent.append($("<div>").addClass("summary").html("<a href='" + summary + "' target='_blank'>Night Summary</a>"));
    // Create image placeholders for this night.
    var exposures = merged[night];
    console.log("Loading " + night + " with " + exposures.length + " exposures...");
    var IMGSRC = "https://portal.nersc.gov/project/desi/users/dkirkby/CI/" + night + "/";
    for(var i = 0; i < exposures.length; i++) {
        var info = exposures[i];
        var div = $("<div>").addClass("thumb").attr("title", info["EXPID"]);
        div.append($("<img>", {"data-src": IMGSRC + info["EXPID"] + ".jpg", class: "lazy"}));
        div.click(function() {
            var URL = $(this).find("img").attr("src");
            window.open(URL, "_blank")
        });
        parent.append(div);
    }
    // Trigger lazy image loading.
    $("#content img.lazy").lazy({
        scrollDirection: 'vertical',
        appendScroll: $('.mdl-layout__content'),
        threshold: 1500,
        onError: function(element) {
            console.log('ERROR lazy loading ' + element.data('src'));
        },
    });
}
