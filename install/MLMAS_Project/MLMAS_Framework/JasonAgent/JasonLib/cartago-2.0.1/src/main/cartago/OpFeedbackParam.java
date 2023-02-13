package cartago;

public class OpFeedbackParam<T> implements java.io.Serializable {

	private T value;
	
	public void set(T t){
		value = t;
	}
	
	public T get(){
		return value;
	}
	
	public void copyFrom(OpFeedbackParam<?> param){
		value = ((OpFeedbackParam<T>)param).value;
	}
}
