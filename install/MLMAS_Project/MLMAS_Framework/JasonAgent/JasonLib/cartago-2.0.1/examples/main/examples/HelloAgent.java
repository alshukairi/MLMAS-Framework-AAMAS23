package examples;
import cartago.*;
import cartago.util.agent.*;

public class HelloAgent extends Agent {
	
	public HelloAgent(String name) throws CartagoException {
		super(name);
	}
	
	public void run() {
		try {
			doAction(new Op("println","Hello, world! from "+getName()));
			log("done");
			ActionFeedback af = doActionAsync(new Op("println","Hello again! from "+getName()));
			log("done");
			af.waitForCompletion();
			if (af.succeeded()){
				log("succeded");
			} else {
				log("failed");
			}
		} catch (Exception ex){
			ex.printStackTrace();
		}
	}
}
