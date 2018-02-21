$(document).ready(function() {

  $("form").submit(function(event){
    // stop form submitting normally
    // could just let it submit normally if didn't need asynchronous ajax functionality
    event.preventDefault();

    parent.$.fancybox.close();
    $.ajax({url: "/requests/api/v1.0",  // this is the javascript this not JQuery object $(this)
            type: "POST",
            data: JSON.parse(JSON.stringify($(this).serializeArray())),
            success: function(result){
		       parent.$("#tableBody").DataTable().ajax.reload();
		       parent.bootstrap_alert("Success!", "Request added", "alert-success");
                       // by iteself, $ = jQuery.
                       // i.e. could use in the html onclick="parent.jQuery.fancybox.close();"
                    }
    });

  });

});