// Global variable to avoid changing device list if there are no changes to it
var checksum = ''

function populate_devices(){
  // Populates device accordion using data from server
  $.post("/devices", function(raw){

    //  Check if any changes have been made        
    if(checksum == JSON.stringify(raw)){
      return;
    }
    else{
      checksum = JSON.stringify(raw);
    }

    // Use mustache to populate the accordion
    $.get("devices.mustache.html", function(template){
      var rendered = Mustache.render(template, jQuery.parseJSON(raw));
      $('#accordion').html(rendered);

      // Set response button on click to update the modal
      $(".response-btn").click(function(event){
        // Get device UDID and command UUID
        var udid = $(this).closest(".panel").attr("id");
        var uuid = $(this).attr("id");

        // Access /response to get the response string
        $.post("/response", JSON.stringify({"UDID":udid, "UUID":uuid}), function(data){
          $("#modal_body").html(data);
        });
      });

      // Puts HTML content inside the popover
      $(".trigger").popover({
        html: true,
        title: function () {
          return $(this).parent().find('.head').html();
        },
        content: function () {
          return $(this).parent().find('.content').html();
        }
      });

      // Submit input group when submit button clicked
      $('body').on('click', '.popover-submit', function(){
        // Get UDID and form values
        var udid = $(this).attr("id");
        var name = $(this).parent().find("#input-name").val();
        var owner = $(this).parent().find("#owner-name").val();
        var location = $(this).parent().find("#location-name").val();

        // POST data to /metadata endpoint
        $.post("/metadata", JSON.stringify({"UDID":udid,"name":name,"owner":owner,"location":location}), function(){});

        $("#metadatapopover".concat(udid)).popover("hide");
      });

    });
  });
}
