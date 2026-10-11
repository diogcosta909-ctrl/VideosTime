DOORS=[(2.4,3.0,3.0,3.4,'brick'),(5.2,5.6,6.2,6.5,'pit'),(8.6,9.0,9.6,10.0,'sky'),(11.4,11.8,12.4,12.7,'lobby')]
def doorinfo(T):
    for a,b,c,d_,k in DOORS:
        if a<=T<d_: return k,(smooth((T-a)/(b-a)) if T<c else 1-smooth((T-c)/(d_-c)))
    return None,0.0
def dispC(T):
    if T<2.0: return '1'
    if T<3.4: return '2'
    if T<5.2: return str(2-min(5,int((T-3.4)/1.8*6)))
    if T<6.5: return '-3'
    if T<8.6: return str(-3+min(102,int((T-6.5)/2.1*102)))
    if T<10.0: return '99'
    if T<11.4: return str(99-int((T-10)/1.4*98))
    if T<12.7: return '1'
    return '2'
def stC(T):
    if T<1.2: return (170,796),0.05,((-1.4+0.25*math.sin(T*25),-1.55),(0.1,0.0)),STAND,'run'
    if T<2.4: return (240,806+4*math.sin(T*40)),0.0,((0.9,1.7),(-0.9,-1.7)),((0.5,-0.4),(-0.5,0.4)),'shock'
    if T<3.4: return stand(240,'wtf')
    if T<5.2:
        u=smooth((T-3.4)/0.5); y=796-130*u+8*math.sin(T*6)
        return (240+10*math.sin(T*3),y),0.1*math.sin(T*4),((PI-0.5,PI-0.2),(PI+0.5,PI+0.2)),((0.25+0.1*math.sin(T*9),0.3),(-0.2,0.2)),'shock'
    if T<5.6:
        u=smooth((T-5.2)/0.4); return (240,lerp(666,796,u)),0.0,((PI-0.5,PI-0.2),(PI+0.5,PI+0.2)),STAND,'shock'
    if T<6.5: return stand(240,'shock')
    if T<8.6: return (240+3*math.sin(T*50),816),0.0,((0.9,1.7),(-0.9,-1.7)),((0.6,-0.5),(-0.6,0.5)),'dead' if int(T*6)%2 else 'shock'
    if T<10.0: return stand(240,'wtf')
    if T<11.4: return stand(240+2*math.sin(T*30),'run')
    if T<11.9: return stand(240,'happy')
    if T<12.5: return fall((T-11.9)/0.6,240,620,'shock')
    if T<14.0: return lying(620)
    if T<14.5: return tumble((T-14.0)/0.5,620,'wtf')
    return stand(620,'wtf')
def content(d,k,T):
    x0,y0,x1,y1=400,560,660,932
    if k=='brick':
        rect(d,x0,y0,x1,y1,fill=(170,80,60),out=None)
        for r in range(0,372,31):
            line(d,[(x0,y0+r),(x1,y0+r)],w=3,col=(110,50,40))
            for c in range(0,260,52): line(d,[(x0+c+(26 if (r//31)%2 else 0),y0+r),(x0+c+(26 if (r//31)%2 else 0),y0+r+31)],w=3,col=(110,50,40))
        rect(d,450,700,610,760,fill=(255,230,120),w=4,rad=4); text(d,(530,730),'ENTRE PISOS',24)
    elif k=='pit':
        rect(d,x0,y0,x1,y1,fill=(14,10,16),out=None)
        sh=4*math.sin(T*40)
        for ex in (480,580): ell(d,(ex+sh,720),34,24,fill=(255,40,40),w=0); ell(d,(ex+sh,720),9,22,fill=(10,0,0),out=None)
        for i in range(8): poly(d,[(430+i*28+sh,820),(444+i*28+sh,880),(458+i*28+sh,820)],(255,255,255),2)
    elif k=='sky':
        rect(d,x0,y0,x1,y1,fill=(110,190,255),out=None)
        for cx,cy,r in ((480,700,40),(560,740,52),(450,820,34),(620,860,44)): circ(d,(cx,cy),r,fill=(255,255,255),out=None)
        px=lerp(700,300,(T-8.6)/1.4); rect(d,px,640,px+70,664,fill=(240,240,250),w=4,rad=10); poly(d,[(px+35,650),(px+50,610),(px+62,650)],(240,240,250),3); circ(d,(px+14,652),5,fill=(120,170,230),w=2)
        rect(d,x0+30,590,x0+150,630,fill=(255,230,120),w=4,rad=4); text(d,(x0+90,610),'PISO 99',24)
    else:
        rect(d,x0,y0,x1,y1,fill=(238,226,200),out=None); rect(d,x0,900,x1,932,fill=(190,170,140),out=None)
        rect(d,440,620,540,680,fill=(255,230,120),w=4,rad=4); text(d,(490,650),'PISO 1',30)
        rect(d,420,780,470,900,fill=(120,170,100),w=4,rad=6)
        text(d,(580,760),'ESCALERAS →',22)
def worldC(d,T):
    rect(d,-10,-300,730,932,fill=(150,156,172),out=None)
    for x in range(0,730,90): line(d,[(x,0),(x,932)],w=3,col=(128,134,150))
    rect(d,-10,932,730,1700,fill=(80,84,98),out=None); line(d,[(-10,932),(730,932)],w=6)
    # button panel (left)
    rect(d,24,620,110,820,fill=(60,64,80),w=5,rad=10)
    for i,(yy_,lab) in enumerate(((650,'3'),(700,'2'),(750,'1'),(800,'-3'))): circ(d,(67,yy_),16,fill=(255,230,120) if lab=='2' else (200,200,210),w=3); text(d,(67,yy_),lab,18)
    # display
    rect(d,450,470,610,540,fill=(14,14,20),w=5,rad=6); text(d,(530,505),dispC(T),48,(255,70,60) if T<12.7 else (120,255,140))
    if T>=12.9: text(d,(530,560-18),':)',30,(120,255,140))
    # doors + content
    k,o=doorinfo(T)
    rect(d,396,556,664,932,fill=(40,44,56),w=5,rad=2)
    if k: content(d,k,T)
    dw=130*(1-o)
    rect(d,400,560,400+dw,932,fill=(205,210,220),w=5,rad=0); rect(d,660-dw,560,660,932,fill=(205,210,220),w=5,rad=0)
    s=stC(T); look=-1 if T<1.2 else 1
    hd=drawpil(d,s,look)
    if 12.5<=T<14.0: stars(d,hd,T)
    if 5.4<=T<5.9 and False: pass
def hudC(d,T):
    pill(d,110,610,[(150,128,'OBJETIVO',24,(190,196,212),'lm'),(150,160,'PISO 2',34,YEL,'lm'),(380,150,'AHORA',22,(150,156,172),'lm'),(540,150,dispC(T),64,(255,110,100),'mm')])
def camC(T):
    if T<0.25: return 1.2-0.2*(T/0.25),120,800+OFF
    if 2.4<=T<2.8: return 1+0.3*ease((T-2.4)/0.3),520,560+OFF
    if 5.2<=T<6.2: return 1.3,520,740+OFF
    if 8.6<=T<9.4: return 1.25,520,720+OFF
    if 12.2<=T<13.0: return 1+0.2*ease((T-12.2)/0.4),460,800+OFF
    return 1,360,640
CC=dict(name='epC',world=worldC,hud=hudC,cam=camC,EV=[2.4,5.2,8.6,11.4],flash=[2.4,5.2,8.6,11.4],freeze=(5.35,5.6),
 shakes=[(1.2,2.4,7),(3.4,5.2,10),(6.5,8.6,12),(10.0,11.4,8),(11.95,12.4,18)],speed=[(3.4,3.8),(6.5,6.9)],
 caps=[(0,1.2,'Solo quiero ir al piso 2'),(1.2,2.4,'Sube…'),(2.4,3.4,'Piso 2: entre pisos'),(3.4,5.2,'Ahora baja'),(5.2,6.5,'Sótano -3'),(6.5,8.6,'Ahora sube. Mucho'),(8.6,10.0,'Piso 99'),(10.0,11.4,'Casi…'),(11.4,12.5,'Piso 1. Otra vez'),(12.5,14.0,'Me ha echado'),(14.0,15.1,'El ascensor gana')],
 pops=[(2.4,3.0,'¡DING!',330,100,YEL),(5.3,6.0,'¡ROAAAR!',330,100,RED),(8.8,9.4,'¡FIUUUM!',330,86,(150,215,255)),(11.95,12.6,'¡PTUI!',330,100,RED)],
 Ts=(0.2,0.8,1.5,2.2,2.6,3.2,4.0,4.8,5.3,5.45,5.8,6.4,7.4,8.2,8.8,9.3,10.4,11.6,12.2,13.0,14.6))
run(CC)
