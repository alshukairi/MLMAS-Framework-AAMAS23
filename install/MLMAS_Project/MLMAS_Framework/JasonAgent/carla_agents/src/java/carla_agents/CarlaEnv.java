package carla_agents;

import jason.asSyntax.*;
import jason.environment.Environment;


import CarlaSocket.*;

import javax.json.JsonObject;

/* The CARLA Environment class, prepare the Jason agent environment
 * and handle request and actions 
 * (C) University of Aberdeen - Hilal Al Shukairi
 */
public class CarlaEnv extends Environment  {
	JasonCarlaBridge bridge;
	JsonProcessing jsn;
	BeliefsHandler blf_handler;

	public static final Term na = Literal.parseLiteral("no_action");
	 @Override
	 public void init(String[] args) {

	        if (args.length == 1) {
//	        	if (args.length == 1 && args[0].equals("gui")) {
	        	bridge = new JasonCarlaBridge();
	        	jsn = new JsonProcessing();
	        	blf_handler = new BeliefsHandler(this);
	        	
	        	//Starting the sockets threads
	        	bridge.start();
	        	
	        	//Starting the beliefs handler
	        	blf_handler.start();
	        	
	 
	        }
	        
	        System.out.println("Started");
	 }    
	 

	 @Override
	    public boolean executeAction(String ag, Structure action) {

	        boolean result = false;
	     
	        if (action.equals(na)) { // No Action required
	        	JsonObject jsn_no_action = jsn.json_pack_no_action();
	        	bridge.send_message(jsn_no_action.toString() + "\n");
	        	result = true;
	        }
	     // control(metricType,throttle, steer, brake, hand_brake, reverse, repeat)
	        else if (action.getFunctor().equals("control")) {
	        	int metricType = Integer.parseInt(action.getTerm(0).toString());
	        	Double throttle = Double.parseDouble(action.getTerm(1).toString());
	        	Double steer = Double.parseDouble(action.getTerm(2).toString());
	        	Double brake = Double.parseDouble(action.getTerm(3).toString());
	            boolean hand_brake = action.getTerm(4).toString().equals("true");
	            boolean reverse = action.getTerm(5).toString().equals("true");
	            int repeat = Math.round(Math.max(1, 
	            						Float.parseFloat(action.getTerm(6).toString())));
	            
	            JsonObject jsn_control = jsn.json_pack_control(metricType, throttle, steer, 
			            										brake, hand_brake, 
			            										reverse, repeat);
	            bridge.send_message(jsn_control.toString() + "\n");
	            result = true;
	        }
	 
	        if (result) {
	            try {
	                Thread.sleep(10);
	            } catch (Exception e) {}
	        }
	        return result;
	    }
	}
