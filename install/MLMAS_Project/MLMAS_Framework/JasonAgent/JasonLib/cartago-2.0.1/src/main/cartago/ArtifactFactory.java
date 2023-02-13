package cartago;

public abstract class ArtifactFactory implements java.io.Serializable {
	private String name;
	
	public ArtifactFactory(String name){
		this.name = name;
	}
	
	public String getName(){
		return name;
	}
	
	abstract public Artifact createArtifact(String templateName) throws CartagoException ;
}
