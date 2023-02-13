!create_and_use.

+!create_and_use : true
  <- !setupTool(Id);
     .wait(1000);
     // use
     inc;
     // second use specifying the Id
     inc [artifact_id(Id)].

// create the tool
+!setupTool(C): true 
  <- makeArtifact("c0","c4jexamples.Counter",[],C).

  
