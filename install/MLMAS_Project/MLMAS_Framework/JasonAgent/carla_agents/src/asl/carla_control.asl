/* Jason Agent to Act in critical situations
 * To avoid accedent and enhance the driving
 * behavior of the ML model especially at
 * traffic lights.
 * (C) University of Aberdeen, Hilal Al Shukairi.
 */

 // Metrics types:
 // (0) front (1) Crossing (far) (2) Crossing (close) (3) Back
 //	(4) Green Go (5) Move from the box (6) Slow down
//control(MrtricsType,throttle, steer, brake, hand_brake, reverse, repeat)


 // 1. A plan to avoid [close obstacles] (Cars, people, ..etc) collision
 // That are intend or try to cross a road or they are already
 // in front of the car.

+!start(F): f(F,X,_,_, MinY) & MinY < 2.0 & X < 4.5
			& info(F,Sp) & Sp > 0.5 & block(Nf, M) & Nf < M
		<-   control(2, 0.0, 0.0, 1.0, false, false, (Sp*3)). // hard break

 // 2. A plan to avoid [Far obstacles] collision
 // That are moving toward the car from the [Right side].
+!start(F): f(F,X,Y,_, MinY) & f(F2,_,Y2,_, MinY2) & (F-F2) <= 2
			& Y > 0 & Y2 > 0 &  MinY > 2.0 & X < 6 & Y < 4
			& (MinY2 - MinY) > 0.15 & ml_control(F,_,St,_,_,_) & St < 0.1
			& info(F,Sp)
		<-   control(1, 0.0, 0.0, 1.0, false, false, (Sp*3)). // hard break
//			.print("===Avoid Road [Far Crossing (R)] Collision===: ", Sp).

 // 3. A plan to avoid [Far obstacles] collision
 // That are moving toward the car from the [Left side].
+!start(F): f(F,X,Y,_, MinY) & f(F2,_,Y2,_, MinY2) & (F-F2) <= 2
			& Y < 0 & Y2 < 0 &  MinY > 2.0 & X < 6 & Y > -4
			& (MinY2 - MinY) > 0.15  & ml_control(F,_,St,_,_,_) & St > - 0.1
			& info(F,Sp)
		<-   control(1, 0.0, 0.0, 1.0, false, false, (Sp*3)). // hard break
//			.print("===Avoid Road [Far Crossing (L)] Collision===: ", Sp).

 // 4. A plan to avoid [front obstacles] collision
 // That are moving or stopping in front of the car
 // in an early stage to be able to stop in the right time.
+!start(F):  sF(F,_,_,MinX,_) & MinX < 7.9
			& info(F,Sp)  & Sp > 0.01 & ml_control(F,_,St,_,_,_)
			& math.abs(St) < 0.05 & sF(F2,_,_,MinX2,_)
			& (F-F2) <= 2 & (MinX2 - MinX) > 0.1
		<-   control(0, 0.0, 0.0, 1.0, false, false, (Sp)). // hard break
//			.print("===Avoid [front] collision===: ", Sp).

 // 5. Good practice to slow down the speedy car when exiting the
 //    the traffic light box, till the road vision and obstacles
 //     become more clear.
+!start(F): traffic_light(_,_,_,_,_,_,1) & not traffic_light(F,_,_,_,_,_,1)
		  & info(F,S) & S > 4 & ml_control(F,_,St,_,_,_)
		<-   control(6, 0.0, St, 0.4, false, false, 5). // Slow Down
//			.print("=== Slow down After Traffic Light Box===: ", F).

 // 6. A plan to predict a fast moving car from the [back].
 //    and to try to avoid it by moving the car slightly, while it
 //    is in the stop state, and no front obstacle available.
+!start(F): sB(F,_,_,MinX,_) & b(F-1,_,_,MinX2,_) & (MinX2- MinX) > 0.1
		& ml_control(F,_,St,Br,_,_) & not traffic_light(_,"L",_,_,_,_,_)
		& info(F,S) & S < 1.5 & not sF(F,_,_,_,_)
		 <-  control(3, 1.0, St, 0.0, false, false, 10). // Go Forward
//			 .print("===Avoid Collision from the [Back]===: ", F).

 // 7. A plan to predict a fast moving car from the [back].
 //    and to try to avoid it by moving the car slightly, while it
 //    is in the stop state, and there is front obstacle but far by more than 3m.
+!start(F): sB(F,_,_,MinX,_) & b(F-1,_,_,MinX2,_) & (MinX2- MinX) > 0.1
		& ml_control(F,_,St,Br,_,_) & not traffic_light(_,"L",_,_,_,_,_)
		& info(F,S) & S < 1.5 & sF(F,_,_,MinX3,_) & MinX3 > 3
		 <-  control(3, 1.0, St, 0.0, false, false, 10). // Go Forward
//			 .print("===Avoid Collision from the [Back 2]===: ", F).

 // 8. A plan to predict a very close car from the [back].
 //    and to try to continue move from it to avoid accident
 //    if there is no front obstacles.
+!start(F): sB(F,_,_,MinX,_) & MinX < 1.6 & not sF(F,_,_,_,_)
		& ml_control(F,_,St,Br,_,_) & not traffic_light(_,"L",_,_,_,_,_)
		 <-  control(3, 0.8, St, 0.0, false, false, 1). // Go Forward
//			 .print("===Avoid Collision from the [Back 3]===: ", F).

 // 9. A plan to predict a very close car from the [back].
 //    and to try to continue move from it to avoid accident.
 //    if there is front obstacle far more than 1m.
+!start(F): sB(F,_,_,MinX,_) & MinX < 1.6 & sF(F,_,_,MinX3,_) & MinX3 > 1
		& ml_control(F,_,St,Br,_,_) & not traffic_light(_,"L",_,_,_,_,_)
		 <-  control(3, 0.8, St, 0.0, false, false, 1). // Go Forward
//			 .print("===Avoid Collision from the [Back 4]===: ", F).

 // 10. A plan to predict a very close car from the [Left side].
 //    and to try to avoid turning toward it to prevent accident.
+!start(F): l(F,X,_,_,MinY) &  MinY < 1.9 & math.abs(X) < 1.9
		& l(F2,_,_,_,MinY2) & (F-F2) <= 2 & MinY < MinY2
//		& ml_control(F,Tr,St,Br,_,_) & St < -0.05
		<-   control(2, 0.0, 0.1, 1.0, false, false, 1). // Go Forward
//			.print("=== STOP Turning left <<<Left Collision===: ", F).


 // 11. A plan to predict a very close car from the [Right side].
 //    and to try to avoid turning toward it to prevent accident.
+!start(F): r(F,X,_,_,MinY) &  MinY < 1.9 & math.abs(X) < 1.9
			& l(F2,_,_,_,MinY2) & (F-F2) <= 2 & MinY < MinY2
		<-   control(2, 0.0, -0.1, 1.0, false, false, 1). // Go Forward
//			.print("=== STOP Turning Right>>> Collision===: ", F).

 // 12. A plan to move the car when the traffic light turns green.
+!start(F): traffic_light(F,"A","G",_,_,_,_) & ml_control(F,_,St,_,_,_)
		  & not sF(_,_,_,_,_) & info(F,S) & S < 0.5
		<-   control(4, 0.8, St, 0.0, false, false, 3). // Go forward
//			.print("===Traffic Light is Green: Go ===: ", F).

 // 13. A plan to move the car when the car is in the traffic light box
+!start(F): traffic_light(F,"L",_,_,_,_,1)
		  & not sF(_,_,_,_,_)
		  & info(F,Sp) & Sp < 0.1 & ml_control(F,_,St,_,_,_)
		<-   control(5, 0.8, St, 0.0, false, false, 1). // Go forward
//			.print("===Move from Traffic Light Box: Go===: ", F).


+!start(F): traffic_light(F,"L",_,_,_,_,1)
		  & not sF(_,_,_,_,_)
		  & info(F,Sp) & Sp < 0.1 & ml_control(F,_,St,_,_,_)
		<-   control(5, 0.8, St, 0.0, false, false, 1). // Go forward


// 14. Detect Blocks and move the car

+!start(F):  ml_control(F,_,St,_,_,_) & math.abs(St) > 0.1
			 & info(F,Sp) & Sp <= 0 & block(Nf,M) & Nf < M
			&  not traffic_light(F,_,"R",_,_,_,_)
			& f(F,_,_,MinX,_) & MinX < 3
		  <- no_action;
		  	-+block(Nf+1, M);
		  	.print("===Count Move for Block===: ", Nf).

+!start(F): info(F,Sp) & Sp <= 0 & block(Nf,M) & Nf < M
			&  not traffic_light(F,_,"R",_,_,_,_)
			& sF(_,_,_,MinX,_) & MinX < 2
		  <- no_action;
		  	-+block(Nf+1, M);
		  	.print("===Count Move for Block [3]===: ", Nf).

+!start(F): ml_control(F,Th,_,Br,_,_) & Th > 0 & Br < 1
  			 & info(F,Sp) & Sp <= 0.2 & block(Nf,M) & Nf < M
  			&  not traffic_light(F,_,"R",_,_,_,_)
  		  <- no_action;
  		  	-+block(Nf+1, M);
  		  	.print("===Count Move for Block [new]===: ", Nf).

+!start(F): block(Nf, M) & Nf >= M
		   & info(F,Sp) & Sp < 1.0 & not traffic_light(F,_,"R",_,_,_,_)
		   & not sF(F,_,_,_,_)
		  <-  control(5, 0.8, 0.0, 0.0, false, false, 5); // Go forward
		  .print("=== Move for Block sf[1]===: ", Nf).

+!start(F): block(Nf, M) & Nf >= M & not traffic_light(F,_,"R",_,_,_,_)
		   & info(F,Sp) & Sp < 1.0 & f(F,_,Y,MinX,_) & MinX > 2 & Y > 0.05
		  <-  control(5, 0.8, -1.0, 0.0, false, false, 2). // Go forward and turn
		  .print("=== Move for Block sF[2,1]===: ", Nf).
+!start(F): block(Nf, M) & Nf >= M & not traffic_light(F,_,"R",_,_,_,_)
		   & info(F,Sp) & Sp < 1.0 & f(F,_,Y,MinX,_) & MinX > 2 & Y <= -0.05
		  <-  control(5, 0.8, 1.0, 0.0, false, false, 2). // Go forward and turn
		  .print("=== Move for Block sF[2,2]===: ", Nf).

+!start(F): block(Nf, M) & Nf >= M & not traffic_light(F,_,"R",_,_,_,_)
		   & info(F,Sp) & Sp < 1.0 & sF(_,_,_,MinX,_) & MinX <= 1.5
		   & sB(F,_,_,MinX2,_) & MinX2 > 1.5
		  <-  control(5, 0.8, -0.2, 0.0, false, true, 2); // reverse
		  	  .print("=== [Reverse] for Block sF[5]===: ", Nf).

+!start(F): block(Nf, M) & Nf >= M & not traffic_light(F,_,"R",_,_,_,_)
		   & info(F,Sp) & Sp < 1.0 & sF(F,_,_,MinX,_) & MinX <= 2
		   & not sB(F,_,_,_,_)
		  <-  control(5, 0.8, 0.0, 0.0, false, true, 5); // reverse
		  	  .print("=== [Reverse] for Block sF[3]===: ", Nf).

+!start(F): block(Nf, M) & Nf >= M & not traffic_light(F,_,"R",_,_,_,_)
		   & info(F,Sp) & Sp < 1.0 & sF(F,_,_,MinX,_) & MinX <= 2
		   & sB(F,_,_,MinX2,_) & MinX2 > 1.5
		  <-  control(5, 0.8, 0.0, 0.0, false, true, 2); // reverse
		  	  .print("=== [Reverse] for Block sF[4]===: ", Nf).



+!start(F): info(F,Sp) & Sp < 1.0 & block(Nf, M) & Nf >= M
		  <- no_action;
		  	.print("===Count Move for Block [2]===: ", Nf).


+!start(F): stopCount(N) & N > 200
		  & info(F,Sp) & Sp <= 0 & traffic_light(F,_,"G",_,_,_,_)
		  & not sF(F,_,_,_,_)
		<-   control(4, 1.0, 0.0 , 0.0, false, false, 20);
			  -+stopCount(0);
		      .print("=== [Pulse to move] ===: ", N). // Go forward
//===============================

// 15. send back no action, to allow the ML model control.
+!start(F): info(F,Sp) & Sp <= 0 & stopCount(N)
			<- no_action;
			  -+block(0,60);
			  -+stopCount(N+1).
        //.print("=== [Stop] ===: ", N).

+!start(F) <- no_action;
			  -+block(0,60);
			  -+stopCount(0).


// 15. a belied activated when there are new beliefs updated to be considered.
+S::startP(F) <- !start(F).
