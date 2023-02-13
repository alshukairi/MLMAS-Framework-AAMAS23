package CarlaSocket;

import java.io.BufferedReader;
import java.util.Deque;

/* A class to handle all the msgs from the server to Jason
 * (C) University of Aberdeen - Hilal Al Shukairi
 */

public class PublicIn extends Thread{
	private volatile Deque<String> q_server_to_jason;
	private volatile BufferedReader in;
	public boolean stop = false;

	public PublicIn(Deque<String> q_server_to_jason, BufferedReader in) {
		System.out.println("Start public in");
		this.q_server_to_jason = q_server_to_jason;
		this.in = in;
	}


	@Override
	public void run() {
		
		while (!this.stop) {
			if (this.in != null) {
			String s;
			try {
				while((s = this.in.readLine()) != null) {
						this.q_server_to_jason.add(s);		
				}
				break;
			} catch (Exception e) {
					if (!this.stop) break;	
			}

			}

		}
		System.out.println("[Stop] public in");
	}

	
}


