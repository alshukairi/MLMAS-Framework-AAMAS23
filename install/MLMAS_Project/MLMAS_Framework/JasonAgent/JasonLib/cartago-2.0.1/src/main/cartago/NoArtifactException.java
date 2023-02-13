package cartago;

public class NoArtifactException extends CartagoException {

	private String opName;
	
	public NoArtifactException(String opName){
		this.opName = opName;
	}
	
	public String getOpName(){
		return opName;
	}
}
