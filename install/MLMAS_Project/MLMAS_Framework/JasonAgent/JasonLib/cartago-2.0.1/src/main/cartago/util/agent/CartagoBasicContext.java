package cartago.util.agent;

import cartago.*;
import cartago.events.*;
import cartago.security.*;

/**
 * @author the_dark
 *
 */
public class CartagoBasicContext {

	public String name;
	private ICartagoSession session;
	private CartagoListener agentCallback;

	private ActionFeedbackQueue actionFeedbackQueue;
	private ObsEventQueue obsEventQueue; 

	private ObsPropMap obsPropMap;

	private final static IEventFilter firstEventFilter = new IEventFilter(){
		public boolean select(ArtifactObsEvent ev){
			return true;
		}
	}; 

	public CartagoBasicContext(String name){
		super();
		this.name = name;
		agentCallback = new CartagoListener();
		actionFeedbackQueue = new ActionFeedbackQueue();
		obsEventQueue = new ObsEventQueue();
		obsPropMap = new ObsPropMap();
		try {
			session = CartagoService.startSession("default", new cartago.security.AgentIdCredential(name), agentCallback);
		} catch (Exception ex){
			ex.printStackTrace();
		}
	}

	public CartagoBasicContext(String name, String workspaceName){
		super();
		this.name = name;
		agentCallback = new CartagoListener();
		actionFeedbackQueue = new ActionFeedbackQueue();
		obsEventQueue = new ObsEventQueue();
		obsPropMap = new ObsPropMap();
		try {
			session = CartagoService.startSession(workspaceName, new cartago.security.AgentIdCredential(name), agentCallback);
		} catch (Exception ex){
			ex.printStackTrace();
		}
	}
		
	public CartagoBasicContext(String name, String workspaceName, String workspaceHost) {
		super();
		this.name = name;
		agentCallback = new CartagoListener();
		actionFeedbackQueue = new ActionFeedbackQueue();
		obsEventQueue = new ObsEventQueue();
		obsPropMap = new ObsPropMap();
		try {
			session = CartagoService.startRemoteSession(workspaceName, workspaceHost, "default", new AgentIdCredential(name), agentCallback);
		} catch (Exception ex){
			ex.printStackTrace();
		}
	}
	
	
	public ArtifactObsProperty getObsProperty(String name){
		return obsPropMap.getByName(name);
	}
	
	public ActionFeedback doActionAsync(Op op) throws CartagoException {
		long id = session.doAction(op, null, -1);
		ActionFeedback res = new ActionFeedback(id,actionFeedbackQueue);
		return res;
	}

	public ActionFeedback doActionAsync(ArtifactId aid, Op op, long timeout) throws CartagoException {
		long id = session.doAction(aid, op, null, timeout);
		ActionFeedback res = new ActionFeedback(id,actionFeedbackQueue);
		return res;
	}

	public ActionFeedback doActionAsync(Op op, long timeout) throws CartagoException {
		long id = session.doAction(op, null, timeout);
		ActionFeedback res = new ActionFeedback(id,actionFeedbackQueue);
		return res;
	}

	public void doAction(Op op, long timeout) throws CartagoException {
		long id = session.doAction(op, null, timeout);
		ActionFeedback res = new ActionFeedback(id,actionFeedbackQueue);
		try {
			res.waitForCompletion();
		} catch (Exception ex){
			throw new CartagoException();
		}
		try {
			if (res.failed()){
				throw new CartagoException();
			} else {
				Op retOp = res.getOp();
				// if it is a remote op
				if (retOp != op){
					Object[] params = op.getParamValues();
					Object[] newParams = retOp.getParamValues();
					for (int i = 0; i < params.length; i++){
						if (params[i] instanceof OpFeedbackParam<?>){
							((OpFeedbackParam<?>)params[i]).copyFrom(((OpFeedbackParam<?>)newParams[i]));
						}
					}
				}				
			}
		} catch (Exception ex){
			ex.printStackTrace();
			throw new CartagoException();
		}
	}

	public void doAction(Op op) throws CartagoException {
		this.doAction(op, -1);
	}

	public void doAction(ArtifactId aid, Op op, long timeout) throws CartagoException {
		long id = session.doAction(aid, op, null, timeout);
		ActionFeedback res = new ActionFeedback(id,actionFeedbackQueue);
		try {
			res.waitForCompletion();
		} catch (Exception ex){
			throw new CartagoException();
		}
		try {
			if (res.failed()){
				throw new CartagoException();
			} else {
				Op retOp = res.getOp();
				// if it is a remote op
				if (retOp != op){
					Object[] params = op.getParamValues();
					Object[] newParams = retOp.getParamValues();
					for (int i = 0; i < params.length; i++){
						if (params[i] instanceof OpFeedbackParam<?>){
							((OpFeedbackParam<?>)params[i]).copyFrom(((OpFeedbackParam<?>)newParams[i]));
						}
					}
				}				
			}
		} catch (Exception ex){
			throw new CartagoException();
		}
	}

	public void doAction(ArtifactId aid, Op op) throws CartagoException {
		this.doAction(aid,op,-1);
	}

	public Percept fetchPercept() throws InterruptedException {
		ArtifactObsEvent ev = obsEventQueue.fetch(firstEventFilter);
		return new Percept(ev);
	}

	public Percept fetchPercept(IEventFilter filter) throws InterruptedException {
		ArtifactObsEvent ev = obsEventQueue.fetch(filter);
		return new Percept(ev);
	}

	public Percept waitForPercept() throws InterruptedException {
		ArtifactObsEvent ev = obsEventQueue.waitFor(firstEventFilter);
		return new Percept(ev);
	}

	public Percept waitForPercept(IEventFilter filter) throws InterruptedException {
		ArtifactObsEvent ev = obsEventQueue.waitFor(filter);
		return new Percept(ev);
	}

	//Utility methods

	public WorkspaceId joinWorkspace(String wspName, AgentCredential cred) throws CartagoException {
		OpFeedbackParam<WorkspaceId> res = new OpFeedbackParam<WorkspaceId>();
		try{
			doAction(new Op("joinWorkspace", wspName, cred, res), -1);
		} catch (Exception ex){
			throw new CartagoException();
		}
		return res.get();
	}

	public WorkspaceId joinRemoteWorkspace(String wspName, String address, String roleName, AgentCredential cred)  throws CartagoException {
		OpFeedbackParam<WorkspaceId> res = new OpFeedbackParam<WorkspaceId>();
		try{
			doAction(new Op("joinRemoteWorkspace", address, wspName, roleName, cred, res));
		} catch (Exception ex){
			throw new CartagoException();
		}
		return res.get();
	}

	public ArtifactId lookupArtifact(String artifactName) throws CartagoException {
		OpFeedbackParam<ArtifactId> res = new OpFeedbackParam<ArtifactId>();
		try{
			doAction(new Op("lookupArtifact", artifactName, res));
		} catch (Exception ex){
			throw new CartagoException();
		}
		return res.get();
	}

	public ArtifactId makeArtifact(String artifactName, String templateName) throws CartagoException {
		OpFeedbackParam<ArtifactId> res = new OpFeedbackParam<ArtifactId>();
		try{
			doAction(new Op("makeArtifact", artifactName, templateName, new Object[0], res));
		} catch (Exception ex){
			throw new CartagoException();
		}
		return res.get();
	}

	public ArtifactId makeArtifact(String artifactName, String templateName, Object[] params) throws CartagoException {
		OpFeedbackParam<ArtifactId> res = new OpFeedbackParam<ArtifactId>();
		try{
			doAction(new Op("makeArtifact", artifactName, templateName, params, res));
		} catch (Exception ex){
			throw new CartagoException();
		}
		return res.get();
	}

	public void disposeArtifact(ArtifactId artifactId) throws CartagoException {
		try{
			doAction(new Op("disposeArtifact", artifactId));
		} catch (Exception ex){
			throw new CartagoException(); 
		}
	}

	public void focus(ArtifactId artifactId) throws CartagoException {
		try{
			doAction(new Op("focus", artifactId));
		} catch (Exception ex){
			throw new CartagoException();
		}
	}

	public void focus(ArtifactId artifactId, IEventFilter filter) throws CartagoException {
		try{
			doAction(new Op("focus", artifactId, filter));
		} catch (Exception ex){
			throw new CartagoException();
		}
	}
	
	public void stopFocus(ArtifactId artifactId) throws CartagoException {
		try{
			doAction(new Op("stopFocus", artifactId));
		} catch (Exception ex){
			throw new CartagoException();
		}
	}

	public void log(String msg){
		System.out.println("["+name+"] "+msg);
	}

	public String getName() {
		return name;
	}


	class CartagoListener implements ICartagoListener {

		public CartagoListener(){
		}

		public boolean notifyCartagoEvent(CartagoEvent ev) {
			//log("received event: "+ev);
			try {
				if (ev instanceof CartagoActionEvent){
					actionFeedbackQueue.add((CartagoActionEvent)ev);
					if (ev instanceof FocusSucceededEvent){
						FocusSucceededEvent ev1 = (FocusSucceededEvent) ev;
						obsPropMap.addProperties(ev1.getArtifactId(),ev1.getObsProperties());
					} else if (ev instanceof StopFocusSucceededEvent){
						StopFocusSucceededEvent ev1 = (StopFocusSucceededEvent) ev;
						obsPropMap.removeProperties(ev1.getArtifactId());
					}
				} else if (ev instanceof ArtifactObsEvent){
					obsEventQueue.add((ArtifactObsEvent)ev);
					ArtifactObsEvent ev1 = (ArtifactObsEvent) ev;
					cartago.ArtifactObsProperty[] added = ev1.getAddedProperties();
					cartago.ArtifactObsProperty[] changed = ev1.getChangedProperties();
					cartago.ArtifactObsProperty[] removed = ev1.getRemovedProperties();
					if (added!=null){
						for (cartago.ArtifactObsProperty prop: added){
							obsPropMap.add(ev1.getArtifactId(),prop);
						}
					}
					if (changed != null){
						for (cartago.ArtifactObsProperty prop: changed){
							obsPropMap.updateProperty(ev1.getArtifactId(),prop);
						}
					}
					if (removed != null){
						for (cartago.ArtifactObsProperty prop: removed){
							obsPropMap.remove(prop);
						}
					}
				}
			} catch (Exception ex){
				ex.printStackTrace();
			}
			return false;
		}
	}
	

}