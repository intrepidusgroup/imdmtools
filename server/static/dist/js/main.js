$(document).ready(function(){
  // Initial setup
  update_cmds()

  // Start polling
  populate_devices();
  setInterval(populate_devices, 2000);

  // Check for device-specific content and enable if applicable
  if(checkDevice()){
    document.getElementById("showEnroll").style.display="block";
    document.getElementById("showCert").style.display="block";
  }

  // Submit button functionality
  $("#submitcmd").click(function(event){
    var checked_devices = [];

    // Get all selected devices
    $(".row_box").each(function(){
      if(this.checked){
        checked_devices.push($(this).closest(".panel").attr("id"));
      }
    });

    // Input checking.
    if ($("#commands").val()==0){
      alert("Please choose a command.");
    }
    else if (checked_devices.length==0){
      alert("Please choose one or more devices.");
    }
    else{
      // Send AJAX request
      // Variable to pass all necessary data to server
      var parameters = {
        "cmd":$("#commands").val(),
        "dev[]":checked_devices
      };

      // Use stringify to fix odd error with passing just parameters
      $.post("/queue", JSON.stringify(parameters), function(){});
    }
  });
});
