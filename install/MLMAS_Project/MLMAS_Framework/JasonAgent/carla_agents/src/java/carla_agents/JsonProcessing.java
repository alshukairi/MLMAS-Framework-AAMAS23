package carla_agents;
import java.io.StringReader;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;


/* The JsonProcessing class, helper class to
 * pack and unpack JSON msgs.
 * (C) University of Aberdeen - Hilal Al Shukairi
 */
public class JsonProcessing {
	public enum AvailableIDs {
	    noAction(0), control(1), sensors(2),
		socketRestart(3), terminate(4);

	    private int numVal;

	    AvailableIDs(int numVal) {
	        this.numVal = numVal;
	    }

	    public int getID() {
	        return numVal;
	    }
	}

	public JsonProcessing() {
		System.out.println("JSON Processing started");
	}

	public JsonObject json_pack_control(int mT, double throttle
			, double steer
			, double brake
			, boolean hand_brake
			, boolean reverse
			, int repeat) {
	
		JsonObject final_json = Json.createObjectBuilder()
				.add("type", Json.createObjectBuilder().add("id", AvailableIDs.control.getID())
						.add("name", "control")
						.build())
				.add("data", 
						Json.createObjectBuilder().add("mT", mT)
						.add("throttle", throttle)
						.add("steer", steer)
						.add("brake", brake)
						.add("hand_brake", hand_brake)
						.add("reverse", reverse)
						.add("repeat", repeat)
						.build())

				.build();

		return final_json;
	}
	
	
	public JsonObject json_pack_no_action() {
		JsonObject final_json = Json.createObjectBuilder()
				.add("type", Json.createObjectBuilder().add("id", AvailableIDs.noAction.getID())
						.add("name", "No_Action")
						.build())
				.build();

		return final_json;
	}
	
	
	public JsonObject read_json(String msg) {
		try {
			JsonReader jsonReader = Json.createReader(new StringReader(msg));
			JsonObject object = jsonReader.readObject();
			jsonReader.close();
			if (object.getJsonObject("type").getInt("id") > 0){
				return object;	
			}
			return null;
		} catch (Exception e) {
			return null;
		}
	}

}
