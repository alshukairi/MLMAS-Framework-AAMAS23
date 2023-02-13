package CarlaSocket;
import java.net.*;
import java.io.*;
import java.util.*;

/* The Jason Carla bridge class, work in superate threads
 * And handle the communication with the server.
 * (C) University of Aberdeen - Hilal Al Shukairi
 */
public class JasonCarlaBridge extends Thread{
    private Socket clientSocket;

    public volatile  Deque<String> q_server_to_jason = new ArrayDeque<String>();
    public volatile  Deque<String> q_jason_to_server = new ArrayDeque<String>();
    private volatile  Deque<String> q_from_agents = new ArrayDeque<String>();
    
    private volatile PrintWriter out;
    private volatile  BufferedReader in;
//    public BufferedReader q_jason_to_server;
    
    private String SERVER_HOST; 
    private int SERVER_PORT;
    private PublicOut P_Out;
    private PublicIn P_In;
    
    public volatile boolean is_connected = false;
	public volatile boolean stop;
	public volatile boolean is_restart_wait;

	
	public JasonCarlaBridge() {
		 System.out.println("Jason Bridge is started");
		 this.is_restart_wait = false;
		 Properties prop = new Properties(); 
		 try {
			FileInputStream serverConfig = new FileInputStream("config/config.properties");
			try {
				prop.load(serverConfig);
			    this.SERVER_HOST = prop.getProperty("SERVER_IP","127.0.0.1");
			    this.SERVER_PORT = Integer.parseInt(prop.getProperty("SERVER_PORT", "60111"));
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			
			
		} catch (FileNotFoundException e) {
			e.printStackTrace();
		}
	}
	
	
	
	@Override
	public void run() {

		while(!this.stop) {
			boolean chk = (this.is_restart_wait) || (this.P_In == null || !this.P_In.isAlive());
			if(this.is_restart_wait) {
				System.out.println(">>wait Restart<<<");
				this.is_restart_wait = false;
				try {
					Thread.sleep(1000);
				} catch (InterruptedException e) {

				}
			}
			try {
				if(chk) {
					stopThreads();
					if((this.is_connected = connect())) {
						this.P_Out = new PublicOut(this.q_from_agents,
													this.out);	
						this.P_In = new PublicIn(this.q_server_to_jason, 
												this.in);	
						
						this.P_In.start();
						this.P_Out.start();
			
						
					}else {
						stopThreads();
					}
				}
				try {
					Thread.sleep(1000);
				} catch (InterruptedException e) {

				}
			} catch (Exception e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
				stopThreads();
				
			}
			try {
				
				Thread.sleep(1000);
			} catch (InterruptedException e1) {
				// TODO Auto-generated catch block
				e1.printStackTrace();
			}
		}
	stopThreads();
		 
	}
	
	private void stopThreads() {

		if(this.clientSocket != null) {
			try {
				this.clientSocket.close();
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
		}
		
		 if(this.P_Out != null) {
			 this.P_Out.stop = true;
		 }
		 if(this.P_In != null) {
			 this.P_In.stop = true;
		 }
 
	}
	
	public void restartConnection() {
		this.is_restart_wait = true;
	}
	
	private boolean connect() {
		 try {
				clientSocket = new Socket(this.SERVER_HOST, this.SERVER_PORT);
				this.out = new PrintWriter(clientSocket.getOutputStream(), true);
				this.in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
				System.out.println("[Connected with the server]");
				return true;
		 } catch (UnknownHostException e) {
			 stopThreads();
			 return false;
			} catch (IOException e) {
				stopThreads();
		    return false;
			}
		 
	}
	
	
	public void send_message(String msg) {
		this.q_from_agents.add(msg);
	}

}
