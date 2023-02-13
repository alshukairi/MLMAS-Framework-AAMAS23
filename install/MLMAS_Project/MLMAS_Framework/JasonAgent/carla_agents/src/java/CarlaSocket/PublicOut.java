package CarlaSocket;

import java.io.PrintWriter;
import java.util.Deque;


/* A class to handle all the msgs from Jason to server
 * (C) University of Aberdeen - Hilal Al Shukairi
 */

public class PublicOut extends Thread{
	
	 
	public volatile Deque<String> q_from_agents;
	public volatile PrintWriter out;
	public volatile boolean stop = false;
	public PublicOut(Deque<String> q_from_agents, PrintWriter out) {
		System.out.println("Start public out");
		this.q_from_agents = q_from_agents;
		this.out = out;
	}

	@Override
	public void run() {
		while (!this.stop) {
			if (this.out != null && !this.q_from_agents.isEmpty()) {
			try {
			    String msg = this.q_from_agents.pop();
				this.out.println(msg);
			} catch (Exception e) {
				if (!this.stop) break;
			}

			}else {
				Threadsleep(10);
			}
			
				
		}
		System.out.println("[Stop] public out");
	
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
