package carla_agents;

import jason.asSyntax.Literal;

import java.util.NavigableSet;
import java.util.TreeSet;

import javax.json.JsonObject;


/* The Beliefs Handler class, receives all the sensors data
 * and update and manage the beliefs accordingly.
 * (C) University of Aberdeen - Hilal Al Shukairi 
 */

public class BeliefsHandler extends Thread {
	CarlaEnv env;
	public volatile boolean is_reseted;
	String speed;
	public NavigableSet<Integer> q_beliefs_frames = new TreeSet<Integer>();

	public volatile boolean stop;
	private int scenario;

	public BeliefsHandler(CarlaEnv env) {
		System.out.println("BelifsHandler Started");
		this.env = env;
		this.is_reseted = false;
		this.scenario = 0;

	}

	@Override
	public void run() {
		while (!this.stop) {
			if (!this.env.bridge.q_server_to_jason.isEmpty()) {
				message_handler(this.env.bridge.q_server_to_jason.pop());
			} else {
				Threadsleep(10);
			}
		}

	}

	private void message_handler(String msg) {
		JsonObject jsn;
		if ((jsn = this.env.jsn.read_json(msg)) != null) { // Valid JSON file
			int mainId = jsn.getJsonObject("type").getInt("id");

			if (mainId == JsonProcessing.AvailableIDs.sensors.getID()) { // sensor data
//				this.env.clearPercepts();
				if (this.is_reseted) {
					this.is_reseted = false;
					this.env.clearAllPercepts();
					this.q_beliefs_frames.clear();
					this.scenario++;
				}
				JsonObject data_jsn = jsn.getJsonObject("data");

				int current_frame = 0;
				if (data_jsn.containsKey("info")) {
					current_frame = data_jsn.getJsonObject("info").getInt("frame");

					this.q_beliefs_frames.add(current_frame);

					speed = data_jsn.getJsonObject("info").get("speed").toString();

					this.env.addPercept("carla_control",
							Literal.parseLiteral("info(" + current_frame + "," + speed + ")"));

				} else {
					return;
				}

				if (data_jsn.containsKey("ml_control")) {

					String throttle = data_jsn.getJsonObject("ml_control").get("throttle").toString().replace("\"", "");
					String steer = data_jsn.getJsonObject("ml_control").get("steer").toString().replace("\"", "");
					String brake = data_jsn.getJsonObject("ml_control").get("brake").toString().replace("\"", "");
					Boolean hand_brake = data_jsn.getJsonObject("ml_control").getBoolean("hand_brake");
					Boolean reverse = data_jsn.getJsonObject("ml_control").getBoolean("reverse");

					this.env.addPercept("carla_control", Literal.parseLiteral("ml_control(" + current_frame + ","
							+ throttle + "," + steer + "," + brake + "," + hand_brake + "," + reverse + ")"));
				}

				if (data_jsn.containsKey("f"))
					add_obstacle_percept(data_jsn, "f", current_frame);
				if (data_jsn.containsKey("sF"))
					add_obstacle_percept(data_jsn, "sF", current_frame);
				if (data_jsn.containsKey("b"))
					add_obstacle_percept(data_jsn, "b", current_frame);
				if (data_jsn.containsKey("sB"))
					add_obstacle_percept(data_jsn, "sB", current_frame);
				if (data_jsn.containsKey("l"))
					add_obstacle_percept(data_jsn, "l", current_frame);
				if (data_jsn.containsKey("r"))
					add_obstacle_percept(data_jsn, "r", current_frame);

				if (data_jsn.containsKey("traffic_light")) {

					String typ = data_jsn.getJsonObject("traffic_light").get("type").toString();
					String state = data_jsn.getJsonObject("traffic_light").get("state").toString();
					String x = data_jsn.getJsonObject("traffic_light").get("x").toString().replace("\"", "");
					String y = data_jsn.getJsonObject("traffic_light").get("y").toString().replace("\"", "");
					String d = data_jsn.getJsonObject("traffic_light").get("d").toString().replace("\"", "");
					String inBox = data_jsn.getJsonObject("traffic_light").get("inBox").toString();

					this.env.addPercept("carla_control", Literal.parseLiteral("traffic_light(" + current_frame + ","
							+ typ + "," + state + "," + x + "," + y + "," + d + "," + inBox + ")"));

				}

				removePercept(current_frame);
				// Activate Jason Plan
				this.env.addPercept("carla_control",
						Literal.parseLiteral("S" + this.scenario + "::startP(" + current_frame + ")"));

			} else if (mainId == JsonProcessing.AvailableIDs.socketRestart.getID()) {// socket restart
				System.out.println("===Restart===\n");

				this.env.bridge.restartConnection();
				this.is_reseted = true;

			} // end of sensor data
			else if (mainId == JsonProcessing.AvailableIDs.terminate.getID()) {// socket restart
				System.out.println("===Terminate===\n");
			} // end of sensor data
		} else {
			System.out.println("invalid json:\n" + msg);
		}

	}

	private void add_obstacle_percept(JsonObject data_jsn, String key, int current_frame) {
		String x = data_jsn.getJsonObject(key).get("x").toString().replace("\"", "");
		String y = data_jsn.getJsonObject(key).get("y").toString().replace("\"", "");
		String min_x = data_jsn.getJsonObject(key).get("min_x").toString().replace("\"", "");
		String min_y = data_jsn.getJsonObject(key).get("min_y").toString().replace("\"", "");

		this.env.addPercept("carla_control",
				Literal.parseLiteral(key + "(" + current_frame + "," + x + "," + y + "," + min_x + "," + min_y + ")"));
	}

	private void removePercept(int current_frame) {

		int keep_prev_beliefs = 4;
		int frame_to_remove = current_frame - keep_prev_beliefs; // Keep previous value

		Integer frm = this.q_beliefs_frames.floor(frame_to_remove);
		while (frm != null && frm != 0) {

			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("info(" + frm + ",_)"));
			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("ml_control(" + frm + ",_,_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control",
					Literal.parseLiteral("traffic_light(" + frm + ",_,_,_,_,_,_)"));

			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("f(" + frm + ",_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("sF(" + frm + ",_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("b(" + frm + ",_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("sB(" + frm + ",_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("r(" + frm + ",_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control", Literal.parseLiteral("l(" + frm + ",_,_,_,_)"));
			this.env.removePerceptsByUnif("carla_control",
					Literal.parseLiteral("S" + this.scenario + "::startP(" + frm + ")"));

			this.q_beliefs_frames.remove(frm);
			frm = this.q_beliefs_frames.floor(frame_to_remove);
		}

	}

	private void Threadsleep(int i) {
		try {
			Thread.sleep(i);
		} catch (InterruptedException e) {
			// TODO Auto-generated catch block
//			e.printStackTrace();
		}

	}

}
