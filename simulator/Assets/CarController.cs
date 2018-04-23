using UnityEngine;
using System.Collections.Generic;

public class CarController : MonoBehaviour {

	public float transportSpeed;
	public float rotateSpeed;

	public enum Action { 
		Stop, 
		Forward, 
		Backward, 
		TurnLeft, 
		TurnRight, 
		Out, 
		Reset
	}

	public List<GameObject> carSpwans;

	private Action action = Action.Reset;
	private Stack<KeyCode> keyStack = new Stack<KeyCode>();
	private HashSet<KeyCode> keyPressed = new HashSet<KeyCode>();
	private System.Random random = new System.Random();
	private float positionY;

	private float leftDistance;
	private float rightDistance;

	public void Start() {
		keyStack.Push (KeyCode.Space);
		positionY = transform.position.y;
	}

	public void Update() {
		// Query input
		if (Input.GetKeyDown(KeyCode.W))
			KeyDown (KeyCode.W);
		if (Input.GetKeyDown(KeyCode.A))
			KeyDown (KeyCode.A);
		if (Input.GetKeyDown(KeyCode.S))
			KeyDown (KeyCode.S);
		if (Input.GetKeyDown(KeyCode.D))
			KeyDown (KeyCode.D);
		if (Input.GetKeyUp(KeyCode.W))
			KeyUp (KeyCode.W);
		if (Input.GetKeyUp(KeyCode.A))
			KeyUp (KeyCode.A);
		if (Input.GetKeyUp(KeyCode.S))
			KeyUp (KeyCode.S);
		if (Input.GetKeyUp(KeyCode.D))
			KeyUp (KeyCode.D);
		// Apply action
		switch(action) {
		case Action.Forward:
			MoveForward(Time.deltaTime);
			break;
		case Action.Backward:
			MoveBackward(Time.deltaTime);
			break;
		case Action.TurnLeft:
			RotateLeft(Time.deltaTime);
			break;
		case Action.TurnRight:
			RotateRight(Time.deltaTime);
			break;
		case Action.Reset:
			action = Action.Stop;
			Respwan ();
			break;
		}
	}

	public void OnTriggerEnter(Collider other) {
		if (other.tag == "Disqualification") {
			action = Action.Out;
		}
	}

	// Key event

	private void KeyDown(KeyCode keyCode) {
		if (!keyPressed.Contains (keyCode)) 
			KeyApply (keyCode);
			keyPressed.Add (keyCode);
			keyStack.Push (keyCode);
	}

	private void KeyUp(KeyCode keyCode) {
		if (keyPressed.Contains (keyCode))
			keyPressed.Remove (keyCode);
		while (keyStack.Count > 1) {
			if (!keyPressed.Contains (keyStack.Peek ()))
				keyStack.Pop ();
			else
				break;
		}
		KeyApply (keyStack.Peek ());
	}

	private void KeyApply(KeyCode keyCode) {
		switch (keyCode) {
		case KeyCode.Space:
			Stop ();
			break;
		case KeyCode.W:
			Forward ();
			break;
		case KeyCode.S:
			Backward ();
			break;
		case KeyCode.A:
			TurnLeft ();
			break;
		case KeyCode.D:
			TurnRight ();
			break;
		}
	}

	// Status operation
		
	public void Stop() {
		if (!isOut())
			action = Action.Stop;
	}

	public void Forward() {
		if (!isOut())
			action = Action.Forward;
	}

	public void Backward() {
		if (!isOut())
			action = Action.Backward;
	}

	public void TurnLeft() {
		if (!isOut())
			action = Action.TurnLeft;
	}

	public void TurnRight() {
		if (!isOut())
			action = Action.TurnRight;
	}

	public void Reset() {
		action = Action.Reset;
	}

	public bool isOut() {
		return action == Action.Out;
	}

	// Movement operations

	public void MoveForward(float deltaTime) {
		transform.position += transform.forward * transportSpeed * deltaTime;
	}

	public void MoveBackward(float deltaTime) {
		transform.position += transform.forward * -transportSpeed * deltaTime;
	}

	public void RotateLeft(float deltaTime) {
		transform.Rotate(Vector3.up * -rotateSpeed * deltaTime, Space.World);
	}

	public void RotateRight(float deltaTime) {
		transform.Rotate(Vector3.up * rotateSpeed * deltaTime, Space.World);
	}

	public void Respwan() {
		int index = random.Next (carSpwans.Count);
		Vector3 position = carSpwans [index].transform.position;
		position.y = positionY;
		transform.position = position;
		Vector3 angle = transform.eulerAngles;
		angle.y = carSpwans [index].transform.eulerAngles.y;
		transform.eulerAngles = angle;
	}
}
