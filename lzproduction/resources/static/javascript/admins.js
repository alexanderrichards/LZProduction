$(document).ready(function () {
  $(".checkbox input").change(function(){
    var chkbox = $(this);
    $.ajax({url: "/admins/api/v1.0" + chkbox.attr("id"),
            type: "PUT",
            data: {"admin": chkbox.prop("checked")}});
  });
});