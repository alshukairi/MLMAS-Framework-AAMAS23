package examples;

import cartago.*;

public class ArtifactWithFailure extends Artifact {

	@OPERATION void testFail(){		
		log("executing testFail..");
		failed("Failure msg", "reason", "test",303);
	}
	
}
