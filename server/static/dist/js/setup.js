function update_cmds(){
  // Populate command list
  $.post("/getcommands", function(cmd_list){
    cmds = JSON.parse(cmd_list);
    x = document.getElementById("commands");
    x.options.length = 0
    x.options[x.options.length] = new Option("Select Command", "", true, false);
    for(i=0;i<cmds.length;i++){
      x.options[x.options.length] = new Option(cmds[i][0], cmds[i][1]);
    }
  });
}

function checkDevice(){
  // Returns true if site is accessed using an iDevice
  var agent = navigator.userAgent;
  if (agent.match(/(iPhone|iPod|iPad)/)){
    return true;
  }
  return false;
}
