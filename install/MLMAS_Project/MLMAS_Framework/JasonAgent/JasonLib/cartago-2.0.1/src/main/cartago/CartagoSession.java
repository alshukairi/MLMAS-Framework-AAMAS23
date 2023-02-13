package cartago;

import java.util.HashMap;
import java.util.concurrent.atomic.*;
import cartago.events.*;

public class CartagoSession implements ICartagoSession, ICartagoCallback {

	// one context for workspace, the agent can work in multiple workspaces
	private HashMap<WorkspaceId, ICartagoContext> contexts;
	
	private ICartagoContext currentContext;
	private WorkspaceId currentWspId;
	
	// queue where percepts are notified by the environment
	private java.util.concurrent.ConcurrentLinkedQueue<CartagoEvent> perceptQueue;
	
	private ICartagoListener agentArchListener;
	private AtomicLong actionId;
	
	CartagoSession(ICartagoListener listener)  throws CartagoException {
		contexts = new HashMap<WorkspaceId, ICartagoContext>();
		perceptQueue = new java.util.concurrent.ConcurrentLinkedQueue<CartagoEvent>(); 
		agentArchListener = listener;
		actionId = new AtomicLong(0);
	}

    void setInitialContext(WorkspaceId wspId, ICartagoContext startContext){
		contexts.put(wspId, startContext);
		currentContext = startContext;
		currentWspId = wspId;
	}
	
	public long doAction(ArtifactId aid, Op op, IAlignmentTest test, long timeout) throws CartagoException {
		long actId = actionId.incrementAndGet();
		ICartagoContext ctx = null;
		synchronized (contexts){
			ctx = contexts.get(aid.getWorkspaceId());
		}
		if (ctx != null){
			ctx.doAction(actId, aid, op, test, timeout);
			return actId;
		} else {
			throw new CartagoException("Wrong workspace.");
		}
	}
	
	public long doAction(WorkspaceId wspId, String artName, Op op, IAlignmentTest test, long timeout) throws CartagoException {
		long actId = actionId.incrementAndGet();
		ICartagoContext ctx = null;
		synchronized (contexts){
			ctx = contexts.get(wspId);
		}
		if (ctx != null){
			ctx.doAction(actId, artName, op, test, timeout);
			return actId;
		} else {
			throw new CartagoException("Wrong workspace.");
		}
	}

	public long doAction(WorkspaceId wspId, Op op, IAlignmentTest test, long timeout) throws CartagoException {
		long actId = actionId.incrementAndGet();
		ICartagoContext ctx = null;
		synchronized (contexts){
			ctx = contexts.get(wspId);
		}
		if (ctx != null){
			ctx.doAction(actId, op, test, timeout);
			return actId;
		} else {
			throw new CartagoException("Wrong workspace.");
		}
	}	

	public long doAction(String artName, Op op, IAlignmentTest test, long timeout) throws CartagoException {
		long actId = actionId.incrementAndGet();
		if (currentContext != null){
			currentContext.doAction(actId, artName, op, test, timeout);
			return actId;
		} else {
			throw new CartagoException("Wrong workspace.");
		}
	}

	public long doAction(Op op, IAlignmentTest test, long timeout) throws CartagoException {
		long actId = actionId.incrementAndGet();
		if (currentContext != null){
			//System.out.println("EXECUTING "+op+" in "+currentContext.getWorkspaceId());
			currentContext.doAction(actId, op, test, timeout);
			return actId;
		} else {
			throw new CartagoException("Wrong workspace.");
		}
	}	
	
	// local 

	public WorkspaceId getCurrentWorkspace(){
		return currentWspId;
	}
	
	public void setCurrentWorkspace(WorkspaceId wspId) throws CartagoException {
		synchronized (contexts){
			ICartagoContext ctx = contexts.get(wspId);
			if (ctx != null){
				currentContext = ctx;
				currentWspId = wspId;
			} else {
				for (java.util.Map.Entry<WorkspaceId,ICartagoContext> c: contexts.entrySet()){
					System.out.println(c.getKey()+" "+ctx);
				}
				throw new CartagoException("Wrong workspace "+wspId);
			}
		}
	}
	
	// 

	/**
	 * Fetch a new percept.
	 * 
	 * To be called in the sense stage
	 * of the agent execution cycle.
	 * 
	 */
	public CartagoEvent fetchNextPercept(){
		return  perceptQueue.poll();
	}

	private void checkWSPEvents(CartagoEvent ev){
		if (ev instanceof JoinWSPSucceededEvent){
			JoinWSPSucceededEvent wspev = (JoinWSPSucceededEvent)ev;
			ICartagoContext context = wspev.getContext();
			currentWspId = wspev.getWorkspaceId();
			//System.out.println("SWITCHED TO "+currentWspId);
			currentContext = context;
			synchronized (contexts){
				contexts.put(currentWspId, context);
				// System.out.println("WSP ADDED "+currentWspId);
			}
		} else if (ev instanceof QuitWSPSucceededEvent){
			QuitWSPSucceededEvent wspev = (QuitWSPSucceededEvent)ev;
			WorkspaceId wspId = wspev.getWorkspaceId();
			synchronized (contexts){
				ICartagoContext ctx = contexts.remove(wspId);
				if (currentContext == ctx){
					if (contexts.size() > 0){
						currentContext = contexts.values().iterator().next();
						try {
							currentWspId = currentContext.getWorkspaceId();
						} catch(Exception ex){
							ex.printStackTrace();
						}
					} else {
						currentContext = null;
					}
				}
			}
		}
	}
	
	public void notifyCartagoEvent(CartagoEvent ev){
		//System.out.println("NOTIFIED "+ev.getId()+" "+ev.getClass().getCanonicalName());
		checkWSPEvents(ev);
		boolean keepEvent = true;
		if (agentArchListener!=null){
			keepEvent = agentArchListener.notifyCartagoEvent(ev);
		}
		if (keepEvent){
			perceptQueue.add(ev);
		} 
	}
	
	
}
