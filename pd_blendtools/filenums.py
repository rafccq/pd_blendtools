from collections import namedtuple

FILE_CA51GUARD               = 0x003e
FILE_CAREA51GUARD            = 0x003f
FILE_CCARRINGTON             = 0x0040
FILE_CCASSANDRA              = 0x0041
FILE_CDARK_COMBAT            = 0x0042
FILE_CDARK_FROCK             = 0x0043
FILE_CDARK_TRENCH            = 0x0044
FILE_CDDSHOCK                = 0x0045
FILE_CDD_SECGUARD            = 0x0046
FILE_CDJBOND                 = 0x0047
FILE_CDRCARROLL              = 0x0048
FILE_CELVIS                  = 0x0049
FILE_CELVIS1                 = 0x004a
FILE_CEYESPY                 = 0x004b
FILE_CFEM_GUARD              = 0x004c
FILE_CLABTECH                = 0x004d
FILE_CMRBLONDE               = 0x004e
FILE_COFFICEWORKER           = 0x004f
FILE_COFFICEWORKER2          = 0x0050
FILE_COVERALL                = 0x0051
FILE_CSECRETARY              = 0x0052
FILE_CSKEDAR                 = 0x0053
FILE_CSTRIPES                = 0x0054
FILE_CTESTCHR                = 0x0055
FILE_CTHEKING                = 0x0056
FILE_CTRENT                  = 0x0057
FILE_GCARTBLUE               = 0x0058
FILE_GCARTRIDGE              = 0x0059
FILE_GCARTRIFLE              = 0x005a
FILE_GCARTSHELL              = 0x005b
FILE_GJOYPAD                 = 0x005c
FILE_PA51_CRATE1             = 0x005d
FILE_PA51_CRATE2             = 0x005e
FILE_PA51_CRATE3             = 0x005f
FILE_PA51_EXP1               = 0x0060
FILE_PA51_EXP2               = 0x0061
FILE_PA51_HORIZ_DOOR_BOT     = 0x0062
FILE_PA51_HORIZ_DOOR_GL      = 0x0063
FILE_PA51_HORIZ_DOOR_SECRET  = 0x0064
FILE_PA51_HORIZ_DOOR_TOP     = 0x0065
FILE_PA51_LIFT_CONTROL       = 0x0066
FILE_PA51_LIFT_HANGAR        = 0x0067
FILE_PA51_LIFT_STORE         = 0x0068
FILE_PA51_LIFT_THINWALL      = 0x0069
FILE_PA51_UNEXP1             = 0x006a
FILE_PA51_UNEXP2             = 0x006b
FILE_PA51_UNEXP3             = 0x006c
FILE_PA51_VERT_DOOR_LEFT     = 0x006d
FILE_PA51_VERT_DOOR_RIGHT    = 0x006e
FILE_PA51_VERT_DOOR_ST       = 0x006f
FILE_PA51BOARD               = 0x0070
FILE_PA51CHAIR               = 0x0071
FILE_PA51DESKENT             = 0x0072
FILE_PA51DIVIDE              = 0x0073
FILE_PA51SCREEN              = 0x0074
FILE_PA51TABLE               = 0x0075
FILE_PA51TROLLEY             = 0x0076
FILE_PA51WASTEBIN            = 0x0077
FILE_PAIVILLABOT1            = 0x0078
FILE_PAIVILLABOT2            = 0x0079
FILE_PAIVILLABOT3            = 0x007a
FILE_PAIVILLADOOR1           = 0x007b
FILE_PAIVILLADOOR2A          = 0x007c
FILE_PAIVILLADOOR4           = 0x007d
FILE_PAIVILLAWINDMILL        = 0x007e
FILE_PAL_AIRLOCK             = 0x007f
FILE_PAL_DOCKLIFT            = 0x0080
FILE_PALDOOR_L               = 0x0081
FILE_PALDOOR_R               = 0x0082
FILE_PBORG_CRATE             = 0x0083
FILE_PCASE                   = 0x0084
FILE_PCH_SHUTTER1            = 0x0085
FILE_PCHRBRIEFCASE           = 0x0086
FILE_PCHRBUG                 = 0x0087
FILE_PCHRDATATHIEF           = 0x0088
FILE_PCRYPTDOOR1B            = 0x0089
FILE_PDD_AC_EXP              = 0x008a
FILE_PDD_AC_UNEXP            = 0x008b
FILE_PDD_ACBOT_EXP           = 0x008c
FILE_PDD_ACBOT_UNEXP         = 0x008d
FILE_PDD_BANNER              = 0x008e
FILE_PDD_CHAIR               = 0x008f
FILE_PDD_DECODOOR            = 0x0090
FILE_PDD_DESK                = 0x0091
FILE_PDD_FANROOF             = 0x0092
FILE_PDD_FANWALL             = 0x0093
FILE_PDD_HOVCAB              = 0x0094
FILE_PDD_HOVCAR              = 0x0095
FILE_PDD_HOVCOP              = 0x0096
FILE_PDD_HOVERCOPTER         = 0x0097
FILE_PDD_HOVMOTO             = 0x0098
FILE_PDD_HOVTRUCK            = 0x0099
FILE_PDD_LAB_CAUTION         = 0x009a
FILE_PDD_LAB_CAUTIONTOP      = 0x009b
FILE_PDD_LAB_DOOR_BS         = 0x009c
FILE_PDD_LAB_DOOR_SEC        = 0x009d
FILE_PDD_LAB_DOOR_WIND       = 0x009e
FILE_PDD_LAB_HAZARD          = 0x009f
FILE_PDD_LAB_RESTRICTED      = 0x00a0
FILE_PDD_LAB_SECTOR2BOT      = 0x00a1
FILE_PDD_LAB_SECTOR2TOP      = 0x00a2
FILE_PDD_LAB_SECTOR3         = 0x00a3
FILE_PDD_LAB_SECTOR3TOP      = 0x00a4
FILE_PDD_LAB_SECTOR3WIND     = 0x00a5
FILE_PDD_LAB_SECTOR4TOP      = 0x00a6
FILE_PDD_LIFTDOOR            = 0x00a7
FILE_PDD_LIFTR               = 0x00a8
FILE_PDD_OFFICEDOOR          = 0x00a9
FILE_PDD_PLANTRUBBER         = 0x00aa
FILE_PDD_PLANTSPIDER         = 0x00ab
FILE_PDD_PLANTSPIKE          = 0x00ac
FILE_PDD_REDARM              = 0x00ad
FILE_PDD_REDSOFA             = 0x00ae
FILE_PDD_SECRETDOOR          = 0x00af
FILE_PDD_SECRETDOOR2         = 0x00b0
FILE_PDD_SERVICEDOOR         = 0x00b1
FILE_PDD_STONEDESK           = 0x00b2
FILE_PDD_VERTBLIND           = 0x00b3
FILE_PDD_WINDDOOR            = 0x00b4
FILE_PDD_WINDOW              = 0x00b5
FILE_PDDJUMPSHIP             = 0x00b6
FILE_PDOOR1A_G5              = 0x00b7
FILE_PDOOR1ATRI_G5           = 0x00b8
FILE_PDOOR1B_G5              = 0x00b9
FILE_PDOOR2_G5               = 0x00ba
FILE_PDOOR2A_G5              = 0x00bb
FILE_PDOOR4A_G5              = 0x00bc
FILE_PDOOR4B_G5              = 0x00bd
FILE_PDOOR_ROLLERTRAIN       = 0x00be
FILE_PDOORCONSOLE            = 0x00bf
FILE_PDR_CAROLL_DOOR         = 0x00c0
FILE_PDR_CAROLL_DOOR_BASE    = 0x00c1
FILE_PDR_CAROLL_DOOR_BLEFT   = 0x00c2
FILE_PDR_CAROLL_DOOR_BMAIN   = 0x00c3
FILE_PDR_CAROLL_DOOR_BRIGHT  = 0x00c4
FILE_PDR_CAROLL_DOOR_LEFT    = 0x00c5
FILE_PDR_CAROLL_DOOR_MAIN    = 0x00c6
FILE_PDR_CAROLL_DOOR_RIGHT   = 0x00c7
FILE_PDROPSHIP               = 0x00c8
FILE_PDUMPSTER               = 0x00c9
FILE_PEXPLOSIONBIT           = 0x00ca
FILE_PFLAG                   = 0x00cb
FILE_PG5_ESCDOORDOWN         = 0x00cc
FILE_PG5_ESCDOORDOWNBOOM     = 0x00cd
FILE_PG5_ESCDOORUP           = 0x00ce
FILE_PG5_ESCDOORUPBOOM       = 0x00cf
FILE_PG5_MAINFRAME           = 0x00d0
FILE_PG5SAFEDOOR             = 0x00d1
FILE_PG5CARLIFTDOOR          = 0x00d2
FILE_PGOLDENEYELOGO          = 0x00d3
FILE_PHOOVERBOT              = 0x00d4
FILE_PHOVBIKE                = 0x00d5
FILE_PHOVERBED               = 0x00d6
FILE_PHOVERCRATE1            = 0x00d7
FILE_PLASDOOR                = 0x00d8
FILE_PMARKER                 = 0x00d9
FILE_PMEDLABWIN1             = 0x00da
FILE_PMEDLABWIN2             = 0x00db
FILE_PMODEMBOX               = 0x00dc
FILE_PNINTENDOLOGO           = 0x00dd
FILE_PNLOGO2                 = 0x00de
FILE_PNLOGO3                 = 0x00df
FILE_PNLOGO                  = 0x00e0
FILE_PPC1                    = 0x00e1
FILE_PPDFOUR                 = 0x00e2
FILE_PPDONE                  = 0x00e3
FILE_PPDTHREE                = 0x00e4
FILE_PPDTWO                  = 0x00e5
FILE_PPERFECTDARK            = 0x00e6
FILE_PPOLICECAR              = 0x00e7
FILE_PRAVINELIFT             = 0x00e8
FILE_PROPE                   = 0x00e9
FILE_PSK_CRYOPOD1_BOT        = 0x00ea
FILE_PSK_CRYOPOD1_TOP        = 0x00eb
FILE_PSK_DOOR1               = 0x00ec
FILE_PSK_FIGHTER1            = 0x00ed
FILE_PSK_HANGARDOOR_BOT      = 0x00ee
FILE_PSK_HANGARDOOR_TOP      = 0x00ef
FILE_PSK_SHIP_DOOR1          = 0x00f0
FILE_PSK_SHIP_HOLO1          = 0x00f1
FILE_PSK_SHIP_HOLO2          = 0x00f2
FILE_PSK_SHIP_HULLDOOR1      = 0x00f3
FILE_PSK_SHIP_HULLDOOR2      = 0x00f4
FILE_PSK_SHIP_HULLDOOR3      = 0x00f5
FILE_PSK_SHIP_HULLDOOR4      = 0x00f6
FILE_PSK_UNDER_GENERATOR     = 0x00f7
FILE_PSK_UNDER_TRANS         = 0x00f8
FILE_PSKCREV_EXP1            = 0x00f9
FILE_PSKCREV_UNEXP1          = 0x00fa
FILE_PSKTNL_EXP1             = 0x00fb
FILE_PSKTNL_UNEXP1           = 0x00fc
FILE_PTAXICAB                = 0x00fd
FILE_PTESTERBOT              = 0x00fe
FILE_PTESTOBJ                = 0x00ff
FILE_PTVSCREEN               = 0x0100
FILE_PWINDOW                 = 0x0101
FILE_GTESTGUN                = 0x0193
FILE_CDD_LABTECH             = 0x0194
FILE_PCCTV_PD                = 0x0195
FILE_PCOMHUB                 = 0x0196
FILE_PQUADPOD                = 0x0197
FILE_PPD_CONSOLE             = 0x0198
FILE_CCONNERY                = 0x0199
FILE_CMOORE                  = 0x019a
FILE_CDALTON                 = 0x019b
FILE_CHEADDARK_COMBAT        = 0x019c
FILE_CHEADELVIS              = 0x019d
FILE_CHEADROSS               = 0x019e
FILE_CHEADCARRINGTON         = 0x019f
FILE_CHEADMRBLONDE           = 0x01a0
FILE_CHEADTRENT              = 0x01a1
FILE_CHEADDDSHOCK            = 0x01a2
FILE_CHEADGRAHAM             = 0x01a3
FILE_CHEADDARK_FROCK         = 0x01a4
FILE_CHEADSECRETARY          = 0x01a5
FILE_CHEADCASSANDRA          = 0x01a6
FILE_CHEADTHEKING            = 0x01a7
FILE_CHEADFEM_GUARD          = 0x01a8
FILE_CHEADJON                = 0x01a9
FILE_PLIFT_PLATFORM          = 0x01aa
FILE_PDD_GRATE               = 0x01ab
FILE_PLIGHTSWITCH            = 0x01ac
FILE_PBLASTSHIELD            = 0x01ad
FILE_PLIGHTSWITCH2           = 0x01ae
FILE_PDD_ACCESSDOORUP        = 0x01af
FILE_PDD_ACCESSDOORDN        = 0x01b0
FILE_CDARK_RIPPED            = 0x01b1
FILE_CHEADMARK2              = 0x01b2
FILE_CHEADCHRIST             = 0x01b3
FILE_PLAB_CONTAINER          = 0x01b4
FILE_PLAB_CHAIR              = 0x01b5
FILE_PLAB_TABLE              = 0x01b6
FILE_PLAB_MICROSCOPE         = 0x01b7
FILE_PLAB_MAINFRAME          = 0x01b8
FILE_PDD_LABDOOR             = 0x01b9
FILE_PDD_LAB_DOORTOP         = 0x01ba
FILE_PMULTI_AMMO_CRATE       = 0x01bb
FILE_CHEADRUSS               = 0x01bc
FILE_CHEADGREY               = 0x01bd
FILE_CHEADDARLING            = 0x01be
FILE_CDD_GUARD               = 0x01bf
FILE_CHEADROBERT             = 0x01c0
FILE_CDD_SHOCK               = 0x01c1
FILE_CHEADBEAU               = 0x01c2
FILE_PCHRCHAIN               = 0x01c3
FILE_CDD_SHOCK_INF           = 0x01c4
FILE_CHEADFEM_GUARD2         = 0x01c5
FILE_PROOFGUN                = 0x01c6
FILE_PTDOOR                  = 0x01c7
FILE_CBIOTECH                = 0x01c8
FILE_CFBIGUY                 = 0x01c9
FILE_PGROUNDGUN              = 0x01ca
FILE_CCIAGUY                 = 0x01cb
FILE_CA51TROOPER             = 0x01cc
FILE_CHEADBRIAN              = 0x01cd
FILE_CHEADJAMIE              = 0x01ce
FILE_CHEADDUNCAN2            = 0x01cf
FILE_CHEADBIOTECH            = 0x01d0
FILE_CA51AIRMAN              = 0x0231
FILE_CHEADNEIL2              = 0x0232
FILE_PCI_SOFA                = 0x0233
FILE_PCI_LIFT                = 0x0234
FILE_PCI_LIFTDOOR            = 0x0235
FILE_CCHICROB                = 0x0236
FILE_CSTEWARD                = 0x0237
FILE_CHEADEDMCG              = 0x0238
FILE_CSTEWARDESS             = 0x0239
FILE_CHEADANKA               = 0x023a
FILE_CPRESIDENT              = 0x023b
FILE_CSTEWARDESS_COAT        = 0x023c
FILE_CHEADLESLIE_S           = 0x023d
FILE_PLASERCUT               = 0x023e
FILE_PSK_SHUTTLE             = 0x023f
FILE_CMINISKEDAR             = 0x0240
FILE_PNEWVILLADOOR           = 0x0241
FILE_CNSA_LACKEY             = 0x0242
FILE_CHEADMATT_C             = 0x0243
FILE_CPRES_SECURITY          = 0x0244
FILE_CHEADPEER_S             = 0x0245
FILE_CNEGOTIATOR             = 0x0246
FILE_CHEADEILEEN_T           = 0x0247
FILE_PSK_PILLARLEFT          = 0x0248
FILE_PSK_PILLARRIGHT         = 0x0249
FILE_PSK_PLINTH_T            = 0x024a
FILE_PSK_PLINTH_ML           = 0x024b
FILE_PSK_PLINTH_MR           = 0x024c
FILE_PSK_PLINTH_BL           = 0x024d
FILE_PSK_PLINTH_BR           = 0x024e
FILE_PSK_FL_SHAD_T           = 0x024f
FILE_PSK_FL_SHAD_ML          = 0x0250
FILE_PSK_FL_SHAD_MR          = 0x0251
FILE_PSK_FL_SHAD_BL          = 0x0252
FILE_PSK_FL_SHAD_BR          = 0x0253
FILE_PSK_FL_NOSHAD_T         = 0x0254
FILE_PSK_FL_NOSHAD_ML        = 0x0255
FILE_PSK_FL_NOSHAD_MR        = 0x0256
FILE_PSK_FL_NOSHAD_BL        = 0x0257
FILE_PSK_FL_NOSHAD_BR        = 0x0258
FILE_GHUDPIECE               = 0x0259
FILE_PSK_TEMPLECOLUMN1       = 0x025a
FILE_PSK_TEMPLECOLUMN2       = 0x025b
FILE_PSK_TEMPLECOLUMN3       = 0x025c
FILE_PSK_SUNSHAD1            = 0x025d
FILE_PSK_SUNSHAD2            = 0x025e
FILE_PSK_SUNNOSHAD1          = 0x025f
FILE_PSK_SUNNOSHAD2          = 0x0260
FILE_CG5_GUARD               = 0x0261
FILE_CHEADANDY_R             = 0x0262
FILE_CPELAGIC_GUARD          = 0x0263
FILE_CG5_SWAT_GUARD          = 0x0264
FILE_CALASKAN_GUARD          = 0x0265
FILE_CMAIAN_SOLDIER          = 0x0266
FILE_CHEADBEN_R              = 0x0267
FILE_CHEADSTEVE_K            = 0x0268
FILE_PBARREL                 = 0x0269
FILE_PGLASS_FLOOR            = 0x026a
FILE_PESCA_STEP              = 0x026b
FILE_PMATRIX_LIFT            = 0x026c
FILE_PRUBBLE1                = 0x026d
FILE_PRUBBLE2                = 0x026e
FILE_PRUBBLE3                = 0x026f
FILE_PRUBBLE4                = 0x0270
FILE_CPRESIDENT_CLONE        = 0x0339
FILE_CHEADJONATHAN           = 0x033a
FILE_CHEADMAIAN_S            = 0x033b
FILE_CDARK_AF1               = 0x033c
FILE_PCABLE_CAR              = 0x033d
FILE_PELVIS_SAUCER           = 0x033e
FILE_PSTEWARDESS_TROLLEY     = 0x033f
FILE_PAIRBASE_LIFT_ENCLOSED  = 0x0340
FILE_PAIRBASE_LIFT_ANGLE     = 0x0341
FILE_PAIRBASE_SAFEDOOR       = 0x0342
FILE_PAF1_PILOTCHAIR         = 0x0343
FILE_PAF1_PASSCHAIR          = 0x0344
FILE_CHEADSHAUN              = 0x0345
FILE_PCHRNIGHTSIGHT          = 0x0346
FILE_PCHRSHIELD              = 0x0347
FILE_PCHRFALCON2             = 0x0348
FILE_PCHRLEEGUN1             = 0x0349
FILE_PCHRMAULER              = 0x034a
FILE_PCHRDY357               = 0x034b
FILE_PCHRDY357TRENT          = 0x034c
FILE_PCHRMAIANPISTOL         = 0x034d
FILE_PCHRFALCON2SIL          = 0x034e
FILE_PCHRFALCON2SCOPE        = 0x034f
FILE_PCHRCMP150              = 0x0350
FILE_PCHRAR34                = 0x0351
FILE_PCHRDRAGON              = 0x0352
FILE_PCHRSUPERDRAGON         = 0x0353
FILE_PCHRAVENGER             = 0x0354
FILE_PCHRCYCLONE             = 0x0355
FILE_PCHRMAIANSMG            = 0x0356
FILE_PCHRRCP120              = 0x0357
FILE_PCHRPCGUN               = 0x0358
FILE_PCHRSHOTGUN             = 0x0359
FILE_PCHRSKMINIGUN           = 0x035a
FILE_PCHRDYROCKET            = 0x035b
FILE_PCHRDEVASTATOR          = 0x035c
FILE_PCHRSKROCKET            = 0x035d
FILE_PCHRZ2020               = 0x035e
FILE_PCHRSNIPERRIFLE         = 0x035f
FILE_PCHRCROSSBOW            = 0x0360
FILE_PCHRDRUGGUN             = 0x0361
FILE_PCHRKNIFE               = 0x0362
FILE_PCHRNBOMB               = 0x0363
FILE_PCHRFLASHBANG           = 0x0364
FILE_PCHRGRENADE             = 0x0365
FILE_PCHRTIMEDMINE           = 0x0366
FILE_PCHRPROXIMITYMINE       = 0x0367
FILE_PCHRREMOTEMINE          = 0x0368
FILE_PCHRECMMINE             = 0x0369
FILE_PCHRWPPK                = 0x036a
FILE_PCHRTT33                = 0x036b
FILE_PCHRSKORPION            = 0x036c
FILE_PCHRKALASH              = 0x036d
FILE_PCHRUZI                 = 0x036e
FILE_PCHRMP5K                = 0x036f
FILE_PCHRM16                 = 0x0370
FILE_PCHRFNP90               = 0x0371
FILE_PCHRDYROCKETMIS         = 0x0372
FILE_PCHRSKROCKETMIS         = 0x0373
FILE_PCHRCROSSBOLT           = 0x0374
FILE_PCHRDEVGRENADE          = 0x0375
FILE_PCHRDRAGGRENADE         = 0x0376
FILE_GFALCON2                = 0x0377
FILE_GLEEGUN1                = 0x0378
FILE_GSKPISTOL               = 0x0379
FILE_GDY357                  = 0x037a
FILE_GDY357TRENT             = 0x037b
FILE_GMAIANPISTOL            = 0x037c
FILE_GCMP150                 = 0x037d
FILE_GAR34                   = 0x037e
FILE_GDYDRAGON               = 0x037f
FILE_GDYSUPERDRAGON          = 0x0380
FILE_GK7AVENGER              = 0x0381
FILE_GCYCLONE                = 0x0382
FILE_GMAIANSMG               = 0x0383
FILE_GRCP120                 = 0x0384
FILE_GPCGUN                  = 0x0385
FILE_GSHOTGUN                = 0x0386
FILE_GSKMINIGUN              = 0x0387
FILE_GDYROCKET               = 0x0388
FILE_GDYDEVASTATOR           = 0x0389
FILE_GSKROCKET               = 0x038a
FILE_GZ2020                  = 0x038b
FILE_GSNIPERRIFLE            = 0x038c
FILE_GCROSSBOW               = 0x038d
FILE_GDRUGGUN                = 0x038e
FILE_GKNIFE                  = 0x038f
FILE_GGRENADE                = 0x0390
FILE_GTIMEDMINE              = 0x0391
FILE_GPROXIMITYMINE          = 0x0392
FILE_GREMOTEMINE             = 0x0393
FILE_GWPPK                   = 0x0394
FILE_GTT33                   = 0x0395
FILE_GSKORPION               = 0x0396
FILE_GAK47                   = 0x0397
FILE_GUZI                    = 0x0398
FILE_GMP5K                   = 0x0399
FILE_GM16                    = 0x039a
FILE_GFNP90                  = 0x039b
FILE_GFALCON2LOD             = 0x039c
FILE_GSKMINIGUNLOD           = 0x039d
FILE_PA51_TURRET             = 0x039e
FILE_PPELAGICDOOR            = 0x039f
FILE_PAUTOSURGEON            = 0x049d
FILE_CDARKWET                = 0x049e
FILE_CDARKAQUALUNG           = 0x049f
FILE_CDARKSNOW               = 0x04a0
FILE_CDARKLAB                = 0x04a1
FILE_CFEMLABTECH             = 0x04a2
FILE_CDDSNIPER               = 0x04a3
FILE_CPILOTAF1               = 0x04a4
FILE_CCILABTECH              = 0x04a5
FILE_CCIFEMTECH              = 0x04a6
FILE_CHEADEILEEN_H           = 0x04a7
FILE_CHEADSCOTT_H            = 0x04a8
FILE_CCARREVENINGSUIT        = 0x04a9
FILE_CJONATHON               = 0x04aa
FILE_CCISOLDIER              = 0x04ab
FILE_CHEADSANCHEZ            = 0x04ac
FILE_CHEADDARKAQUA           = 0x04ad
FILE_CHEADDDSNIPER           = 0x04ae
FILE_PLIMO                   = 0x04af
FILE_PPDMENU                 = 0x04b0
FILE_PA51INTERCEPTOR         = 0x04b1
FILE_PA51DISH                = 0x04b2
FILE_PA51RADARCONSOLE        = 0x04b3
FILE_PA51LOCKERDOOR          = 0x04b4
FILE_PG5GENERATOR            = 0x04b5
FILE_PG5DUMPSTER             = 0x04b6
FILE_GAR34LOD                = 0x04b7
FILE_GAVENGERLOD             = 0x04b8
FILE_GCMP150LOD              = 0x04b9
FILE_GCROSSBOWLOD            = 0x04ba
FILE_GCYCLONELOD             = 0x04bb
FILE_GDRUGGUNLOD             = 0x04bc
FILE_GDY357LOD               = 0x04bd
FILE_GDY357TRENTLOD          = 0x04be
FILE_GDEVASTATORLOD          = 0x04bf
FILE_GDYDRAGONLOD            = 0x04c0
FILE_GDYSUPERDRAGONLOD       = 0x04c1
FILE_GKNIFELOD               = 0x04c2
FILE_GLASERLOD               = 0x04c3
FILE_GMAGSECLOD              = 0x04c4
FILE_GMAYANPISTOLLOD         = 0x04c5
FILE_GMAYANSMGLOD            = 0x04c6
FILE_GPCGUNLOD               = 0x04c7
FILE_GRCP120LOD              = 0x04c8
FILE_GROCKETLOD              = 0x04c9
FILE_GSHOTGUNLOD             = 0x04ca
FILE_GSKPISTOLLOD            = 0x04cb
FILE_GSKROCKETLOD            = 0x04cc
FILE_GSNIPERLOD              = 0x04cd
FILE_GZ2020LOD               = 0x04ce
FILE_PCHRCLOAKER             = 0x04cf
FILE_PCHRSPEEDPILL           = 0x04d0
FILE_PBAGGAGECARRIER         = 0x04d1
FILE_PMINESIGN               = 0x04d2
FILE_PCHAMBER                = 0x04d3
FILE_PISOTOPEEXPERIMENT      = 0x04d4
FILE_PISOTOPE                = 0x04d5
FILE_PREACTORDOOR            = 0x04d6
FILE_PSAUCERINSIDE           = 0x04d7
FILE_PVILLASTOOL             = 0x04d8
FILE_PCETANWINDOW1           = 0x04d9
FILE_PCETANWINDOW2           = 0x04da
FILE_PCETANWINDOW3           = 0x04db
FILE_GLASER                  = 0x04df
FILE_PBIGPELAGICDOOR         = 0x04e0
FILE_PSK_JONRUBBLE3          = 0x04e1
FILE_PSK_JONRUBBLE4          = 0x04e2
FILE_PSK_JONRUBBLE5          = 0x04e3
FILE_PSK_JONRUBBLE6          = 0x04e4
FILE_GCOMBATHANDSLOD         = 0x04e5
FILE_PBINOCULARS             = 0x04e6
FILE_PSUBMARINE              = 0x04e7
FILE_PAIRFORCE1              = 0x04e8
FILE_PENGINEPART             = 0x04e9
FILE_PCETROOFGUN             = 0x04f1
FILE_PCETANSMALLDOOR         = 0x04f2
FILE_PPOWERNODE              = 0x04f3
FILE_PCETANBLUEGREENL        = 0x04f4
FILE_PCETANBLUEGREENR        = 0x04f5
FILE_PSKEDARCONSOLE          = 0x04f6
FILE_PSKEDARCONSOLEPANEL     = 0x04f7
FILE_GNBOMB                  = 0x04fc
FILE_GNBOMBLOD               = 0x04fd
FILE_GGRENADELOD             = 0x04fe
FILE_PWEAPONCDOOR            = 0x04ff
FILE_PTARGET                 = 0x0500
FILE_PDEVICESECRETDOOR       = 0x0501
FILE_PCARRINGTONSECRETDOOR   = 0x0502
FILE_PSINISTERPC             = 0x0503
FILE_PSINISTERSTATION        = 0x0504
FILE_PKEYPADLOCK             = 0x0505
FILE_PTHUMBPRINTSCANNER      = 0x0506
FILE_PRETINALOCK             = 0x0507
FILE_PCARDLOCK               = 0x0508
FILE_PGOODSTATION            = 0x0509
FILE_PGOODPC                 = 0x050a
FILE_CSKEDARKING             = 0x050b
FILE_CELVISWAISTCOAT         = 0x050c
FILE_CHEADGRIFFEY            = 0x050d
FILE_CHEADMOTO               = 0x050e
FILE_CHEADKEITH              = 0x050f
FILE_CHEADWINNER             = 0x0510
FILE_CA51FACEPLATE           = 0x0511
FILE_PCHRAUTOGUN             = 0x0512
FILE_PG5BIGCHAIR             = 0x0513
FILE_PG5SMALLCHAIR           = 0x0514
FILE_PKINGSCEPTRE            = 0x0515
FILE_PLABCOAT                = 0x0516
FILE_PCIDOOR1                = 0x0525
FILE_PG5_CHAIR               = 0x0526
FILE_PG5_CHAIR2              = 0x0527
FILE_PDD_WINDOW_FOYER        = 0x0528
FILE_GHAND_JOWETSUIT         = 0x0529
FILE_GHAND_TRENT             = 0x052a
FILE_GHAND_JOFROCK           = 0x052b
FILE_GHAND_JOTRENCH          = 0x052c
FILE_GHAND_DDSNIPER          = 0x052d
FILE_GHAND_PRESIDENT         = 0x052e
FILE_GHAND_JOAF1             = 0x052f
FILE_GHAND_JOPILOT           = 0x0530
FILE_GHAND_CARRINGTON        = 0x0531
FILE_GHAND_MRBLONDE          = 0x0532
FILE_GHAND_CIA               = 0x0533
FILE_GHAND_CIFEMTECH         = 0x0534
FILE_GHAND_FBIARM            = 0x0535
FILE_GHAND_JOSNOW            = 0x0536
FILE_GHAND_VRIES             = 0x0537
FILE_GHAND_DDSECURITY        = 0x0538
FILE_GHAND_TRAGIC_PELAGIC    = 0x0539
FILE_GHAND_STEWARDESS_COAT   = 0x053a
FILE_GHAND_DDLABTECH         = 0x053b
FILE_PCI_CABINET             = 0x053c
FILE_PCI_DESK                = 0x053d
FILE_PCI_CARR_DESK           = 0x053e
FILE_PCI_F_CHAIR             = 0x053f
FILE_PCI_LOUNGER             = 0x0540
FILE_PCI_F_SOFA              = 0x0541
FILE_PCI_TABLE               = 0x0542
FILE_PCV_COFFEE_TABLE        = 0x0543
FILE_PCV_CHAIR1              = 0x0544
FILE_PCV_CHAIR2              = 0x0545
FILE_PCV_SOFA                = 0x0546
FILE_PCV_CHAIR4              = 0x0547
FILE_PCV_LAMP                = 0x0548
FILE_PCV_CABINET             = 0x0549
FILE_PCV_F_BED               = 0x054a
FILE_PPEL_CHAIR1             = 0x054b
FILE_PSK_CONSOLE2            = 0x054c
FILE_PDD_EAR_TABLE           = 0x054d
FILE_PDD_EAR_CHAIR           = 0x054e
FILE_PAIRBASE_TABLE2         = 0x054f
FILE_PAIRBASE_CHAIR2         = 0x0550
FILE_PMISC_CRATE             = 0x0551
FILE_PMISC_IRSPECS           = 0x0552
FILE_CHEADELVIS_GOGS         = 0x0553
FILE_CHEADSTEVEM             = 0x0554
FILE_PA51_ROOFGUN            = 0x0555
FILE_PSK_DRONE_GUN           = 0x0556
FILE_PCI_ROOFGUN             = 0x0557
FILE_PCV_TABLE               = 0x0558
FILE_CDARK_LEATHER           = 0x0559
FILE_CHEADDARK_SNOW          = 0x055a
FILE_CHEADPRESIDENT          = 0x055b
FILE_PCIDOOR1_REF            = 0x055c
FILE_PALASKADOOR_OUT         = 0x055d
FILE_PALASKADOOR_IN          = 0x055e
FILE_PWIREFENCE              = 0x055f
FILE_PRARELOGO               = 0x0560
FILE_CHEAD_VD                = 0x0561
FILE_PKEYCARD                = 0x0563
FILE_PBODYARMOUR             = 0x0564
FILE_PA51GATE_R              = 0x0565
FILE_PA51GATE_L              = 0x0566
FILE_PAF1_LAMP               = 0x0567
FILE_PAF1_TOILET             = 0x0568
FILE_PAF1_DOORBIG2           = 0x0569
FILE_PAF1_PHONE              = 0x056a
FILE_PAF1_CARGODOOR          = 0x056b
FILE_PG5_ALARM               = 0x056c
FILE_PG5_LASER_SWITCH        = 0x056d
FILE_PSK_TEMPLECOLUMN4       = 0x056e
FILE_PCOREHATCH              = 0x056f
FILE_PA51GRATE               = 0x074c
FILE_GECMMINE                = 0x074d
FILE_GCOMMSUPLINK            = 0x074e
FILE_GIRSCANNER              = 0x074f
FILE_PAF1ESCAPEDOOR          = 0x0750
FILE_PPRESCAPSULE            = 0x0751
FILE_PSKEDARBRIDGE           = 0x0752
FILE_PPELAGICDOOR2           = 0x0753
FILE_PTTB_BOX                = 0x0756
FILE_PINSTFRONTDOOR          = 0x0757
FILE_PCHRLASER               = 0x075b
FILE_PBAFTA                  = 0x075c
FILE_PCHRSONICSCREWER        = 0x075d
FILE_PCHRLUMPHAMMER          = 0x075e
FILE_PSKEDARBOMB             = 0x075f
FILE_PEXPLOSIVEBRICK         = 0x0760
FILE_PRESEARCHTAPE           = 0x0761
FILE_PZIGGYCARD              = 0x0762
FILE_PSAFEITEM               = 0x0763
FILE_GHAND_ELVIS             = 0x0764
FILE_PAF1_TABLE              = 0x0765
FILE_GHAND_A51GUARD          = 0x0766
FILE_GHAND_DDSHOCK           = 0x0767
FILE_GHAND_BLACKGUARD        = 0x0768
FILE_GHAND_DDFODDER          = 0x0769
FILE_GHAND_DDBIO             = 0x076a
FILE_GHAND_A51AIRMAN         = 0x076b
FILE_GHAND_G5GUARD           = 0x076c
FILE_GHAND_CISOLDIER         = 0x076d
FILE_PSENSITIVEINFO          = 0x076e
FILE_PRUSSDAR                = 0x076f
FILE_PXRAYSPECS              = 0x0770
FILE_PCHREYESPY              = 0x0771
FILE_PCHRDOORDECODER         = 0x0772
FILE_PBRIEFCASE              = 0x0773
FILE_PSUITCASE               = 0x0774
FILE_PSHUTTLEDOOR            = 0x0775
FILE_PRUINBRIDGE             = 0x0776
FILE_PSECRETINDOOR           = 0x0777
FILE_PSKPUZZLEOBJECT         = 0x0778
FILE_PA51LIFTDOOR            = 0x0779
FILE_CDARK_NEGOTIATOR        = 0x0796
FILE_PCIHUB                  = 0x0797
FILE_PSK_SHIP_DOOR2          = 0x0798
FILE_PSK_WINDOW1             = 0x0799
FILE_PSK_HANGARDOORB_TOP     = 0x079a
FILE_PSK_HANGARDOORB_BOT     = 0x079b
FILE_PAF1_INNERDOOR          = 0x079c
FILE_PLASER_POST             = 0x079d
FILE_PTARGETAMP              = 0x07b2
FILE_PSK_LIFT                = 0x07b3
FILE_PKNOCKKNOCK             = 0x07b4
FILE_PCETANDOOR              = 0x07b5
FILE_PAF1RUBBLE              = 0x07bb
FILE_PDD_DR_NONREF           = 0x07bc
FILE_CHEADTIM                = 0x07bd
FILE_CHEADGRANT              = 0x07be
FILE_CHEADPENNY              = 0x07bf
FILE_CHEADROBIN              = 0x07c0
FILE_CHEADALEX               = 0x07c1
FILE_CHEADJULIANNE           = 0x07c2
FILE_CHEADLAURA              = 0x07c3
FILE_CHEADDAVEC              = 0x07c4
FILE_CHEADKEN                = 0x07c5
FILE_CHEADJOEL               = 0x07c6
FILE_PCETANDOORSIDE          = 0x07c7
FILE_PBUDDYBRIDGE            = 0x07cc
FILE_CHEADCOOK               = 0x07cd
FILE_CHEADPRYCE              = 0x07ce
FILE_CHEADSILKE              = 0x07cf
FILE_CHEADSMITH              = 0x07d0
FILE_CHEADGARETH             = 0x07d1
FILE_CHEADMURCHIE            = 0x07d2
FILE_CHEADWONG               = 0x07d3
FILE_CHEADCARTER             = 0x07d4
FILE_CHEADTINTIN             = 0x07d5
FILE_CHEADMUNTON             = 0x07d6
FILE_CHEADSTAMPER            = 0x07d7
FILE_CHEADJONES              = 0x07d8
FILE_CHEADPHELPS             = 0x07d9
FILE_PJPNLOGO                = 0x07de
FILE_PJPNPD                  = 0x07df

ModelState = namedtuple('ModelState', 'filenum scale')

ModelStates = [
	ModelState(FILE_PROOFGUN,               0x0199),
	ModelState(FILE_PGROUNDGUN,             0x0199),
	ModelState(FILE_PTVSCREEN,              0x0199),
	ModelState(FILE_PBORG_CRATE,            0x0199),
	ModelState(FILE_PWINDOW,                0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PA51_CRATE1,            0x0199),
	ModelState(FILE_PCRYPTDOOR1B,           0x1000),
	ModelState(FILE_PCHRBRIEFCASE,          0x0199),
	ModelState(FILE_PCHRBUG,                0x0199),
	ModelState(FILE_PCHRDATATHIEF,          0x0199),
	ModelState(FILE_PNINTENDOLOGO,          0x0199),
	ModelState(FILE_PDOOR_ROLLERTRAIN,      0x1000),
	ModelState(FILE_PFLAG,                  0x0199),
	ModelState(FILE_PMODEMBOX,              0x0199),
	ModelState(FILE_PDOORCONSOLE,           0x0199),
	ModelState(FILE_PA51_HORIZ_DOOR_TOP,    0x1000),
	ModelState(FILE_PA51_HORIZ_DOOR_BOT,    0x1000),
	ModelState(FILE_PA51_VERT_DOOR_LEFT,    0x1000),
	ModelState(FILE_PA51_VERT_DOOR_RIGHT,   0x1000),
	ModelState(FILE_PA51_VERT_DOOR_ST,      0x1000),
	ModelState(FILE_PA51_HORIZ_DOOR_GL,     0x1000),
	ModelState(FILE_PA51_HORIZ_DOOR_SECRET, 0x1000),
	ModelState(FILE_PA51_CRATE1,            0x1000),
	ModelState(FILE_PA51_CRATE2,            0x1000),
	ModelState(FILE_PA51_CRATE3,            0x1000),
	ModelState(FILE_PA51_EXP1,              0x0199),
	ModelState(FILE_PA51_UNEXP1,            0x1000),
	ModelState(FILE_PA51_EXP2,              0x0199),
	ModelState(FILE_PA51_UNEXP2,            0x1000),
	ModelState(FILE_PA51_UNEXP3,            0x0199),
	ModelState(FILE_PAIVILLADOOR1,          0x1000),
	ModelState(FILE_PAIVILLADOOR2A,         0x1000),
	ModelState(FILE_PAIVILLADOOR4,          0x1000),
	ModelState(FILE_PA51_LIFT_HANGAR,       0x1000),
	ModelState(FILE_PA51_LIFT_CONTROL,      0x1000),
	ModelState(FILE_PA51_LIFT_STORE,        0x1000),
	ModelState(FILE_PA51_LIFT_THINWALL,     0x1000),
	ModelState(FILE_PAIVILLABOT1,           0x1000),
	ModelState(FILE_PAIVILLABOT2,           0x1000),
	ModelState(FILE_PAIVILLABOT3,           0x1000),
	ModelState(FILE_PAIVILLAWINDMILL,       0x1000),
	ModelState(FILE_PHOVERBED,              0x0199),
	ModelState(FILE_PMARKER,                0x1000),
	ModelState(FILE_PALDOOR_R,              0x1000),
	ModelState(FILE_PALDOOR_L,              0x1000),
	ModelState(FILE_PDD_LIFTR,              0x1000),
	ModelState(FILE_PDD_FANROOF,            0x1000),
	ModelState(FILE_PDD_FANWALL,            0x1000),
	ModelState(FILE_PHOVBIKE,               0x0199),
	ModelState(FILE_PDD_OFFICEDOOR,         0x1000),
	ModelState(FILE_PDD_PLANTRUBBER,        0x1000),
	ModelState(FILE_PDD_PLANTSPIKE,         0x1000),
	ModelState(FILE_PDD_PLANTSPIDER,        0x1000),
	ModelState(FILE_PDD_WINDOW,             0x1000),
	ModelState(FILE_PDD_REDSOFA,            0x1000),
	ModelState(FILE_PDD_REDARM,             0x1000),
	ModelState(FILE_PDD_SERVICEDOOR,        0x1000),
	ModelState(FILE_PDD_WINDDOOR,           0x1000),
	ModelState(FILE_PDD_LIFTDOOR,           0x1000),
	ModelState(FILE_PDD_VERTBLIND,          0x1000),
	ModelState(FILE_PDD_DESK,               0x1000),
	ModelState(FILE_PDD_CHAIR,              0x1000),
	ModelState(FILE_PNLOGO,                 0x0199),
	ModelState(FILE_PNLOGO2,                0x0199),
	ModelState(FILE_PNLOGO3,                0x0199),
	ModelState(FILE_PPERFECTDARK,           0x0199),
	ModelState(FILE_PPDONE,                 0x0199),
	ModelState(FILE_PPDTWO,                 0x0199),
	ModelState(FILE_PPDTHREE,               0x0199),
	ModelState(FILE_PPDFOUR,                0x0199),
	ModelState(FILE_PDD_HOVCOP,             0x1000),
	ModelState(FILE_PDD_HOVMOTO,            0x1000),
	ModelState(FILE_PDD_HOVTRUCK,           0x1000),
	ModelState(FILE_PDD_HOVCAR,             0x1000),
	ModelState(FILE_PDD_HOVCAB,             0x1000),
	ModelState(FILE_PDD_AC_UNEXP,           0x1000),
	ModelState(FILE_PDD_AC_EXP,             0x1000),
	ModelState(FILE_PDD_ACBOT_UNEXP,        0x1000),
	ModelState(FILE_PDD_ACBOT_EXP,          0x1000),
	ModelState(FILE_PPC1,                   0x1000),
	ModelState(FILE_PHOVERCRATE1,           0x1000),
	ModelState(FILE_PDROPSHIP,              0x0199),
	ModelState(FILE_PAL_AIRLOCK,            0x1000),
	ModelState(FILE_PAL_DOCKLIFT,           0x1000),
	ModelState(FILE_PCASE,                  0x1000),
	ModelState(FILE_PDD_STONEDESK,          0x1000),
	ModelState(FILE_PMEDLABWIN1,            0x0199),
	ModelState(FILE_PMEDLABWIN2,            0x0199),
	ModelState(FILE_PA51TABLE,              0x1000),
	ModelState(FILE_PA51CHAIR,              0x1000),
	ModelState(FILE_PA51SCREEN,             0x1000),
	ModelState(FILE_PA51WASTEBIN,           0x1000),
	ModelState(FILE_PA51DESKENT,            0x0199),
	ModelState(FILE_PA51TROLLEY,            0x1000),
	ModelState(FILE_PA51DIVIDE,             0x1000),
	ModelState(FILE_PA51BOARD,              0x1000),
	ModelState(FILE_PSKCREV_EXP1,           0x1000),
	ModelState(FILE_PSKCREV_UNEXP1,         0x1000),
	ModelState(FILE_PSKTNL_EXP1,            0x1000),
	ModelState(FILE_PSKTNL_UNEXP1,          0x1000),
	ModelState(FILE_PSK_DOOR1,              0x1000),
	ModelState(FILE_PSK_SHIP_DOOR1,         0x1000),
	ModelState(FILE_PSK_SHIP_HOLO1,         0x1000),
	ModelState(FILE_PSK_SHIP_HOLO2,         0x1000),
	ModelState(FILE_PSK_SHIP_HULLDOOR1,     0x1000),
	ModelState(FILE_PSK_SHIP_HULLDOOR2,     0x1000),
	ModelState(FILE_PSK_SHIP_HULLDOOR3,     0x1000),
	ModelState(FILE_PSK_SHIP_HULLDOOR4,     0x1000),
	ModelState(FILE_PSK_FIGHTER1,           0x1000),
	ModelState(FILE_PSK_CRYOPOD1_TOP,       0x1000),
	ModelState(FILE_PSK_CRYOPOD1_BOT,       0x1000),
	ModelState(FILE_PSK_UNDER_GENERATOR,    0x1000),
	ModelState(FILE_PSK_UNDER_TRANS,        0x1000),
	ModelState(FILE_PSK_HANGARDOOR_TOP,     0x1000),
	ModelState(FILE_PSK_HANGARDOOR_BOT,     0x1000),
	ModelState(FILE_PDOOR2_G5,              0x1000),
	ModelState(FILE_PDOOR1A_G5,             0x1000),
	ModelState(FILE_PDOOR1B_G5,             0x1000),
	ModelState(FILE_PDOOR1ATRI_G5,          0x1000),
	ModelState(FILE_PDOOR2A_G5,             0x1000),
	ModelState(FILE_PDD_DECODOOR,           0x1000),
	ModelState(FILE_PDD_SECRETDOOR,         0x1000),
	ModelState(FILE_PDD_SECRETDOOR2,        0x1000),
	ModelState(FILE_PDDJUMPSHIP,            0x0199),
	ModelState(FILE_PTAXICAB,               0x0199),
	ModelState(FILE_PPOLICECAR,             0x0199),
	ModelState(FILE_PRAVINELIFT,            0x1000),
	ModelState(FILE_PDD_LAB_DOOR_BS,        0x1000),
	ModelState(FILE_PDD_LAB_DOOR_SEC,       0x1000),
	ModelState(FILE_PDD_LAB_DOOR_WIND,      0x1000),
	ModelState(FILE_PHOOVERBOT,             0x0800),
	ModelState(FILE_PTESTERBOT,             0x0800),
	ModelState(FILE_PDD_LAB_SECTOR2BOT,     0x1000),
	ModelState(FILE_PDD_LAB_SECTOR2TOP,     0x1000),
	ModelState(FILE_PDD_LAB_CAUTIONTOP,     0x1000),
	ModelState(FILE_PDD_LAB_HAZARD,         0x1000),
	ModelState(FILE_PDD_LAB_CAUTION,        0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR,        0x1000),
	ModelState(FILE_PDD_LAB_SECTOR3TOP,     0x1000),
	ModelState(FILE_PDD_LAB_SECTOR3,        0x1000),
	ModelState(FILE_PDD_LAB_SECTOR3WIND,    0x1000),
	ModelState(FILE_PDD_HOVERCOPTER,        0x1000),
	ModelState(FILE_PDD_LAB_SECTOR4TOP,     0x1000),
	ModelState(FILE_PDD_LAB_RESTRICTED,     0x1000),
	ModelState(FILE_PDOOR4A_G5,             0x1000),
	ModelState(FILE_PDOOR4B_G5,             0x1000),
	ModelState(FILE_PLASDOOR,               0x1000),
	ModelState(FILE_PG5SAFEDOOR,            0x1000),
	ModelState(FILE_PROPE,                  0x0199),
	ModelState(FILE_PG5_MAINFRAME,          0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_BASE,   0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_MAIN,   0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_LEFT,   0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_RIGHT,  0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_BMAIN,  0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_BLEFT,  0x1000),
	ModelState(FILE_PDR_CAROLL_DOOR_BRIGHT, 0x1000),
	ModelState(FILE_PDD_BANNER,             0x0199),
	ModelState(FILE_PG5_ESCDOORUP,          0x1000),
	ModelState(FILE_PG5_ESCDOORUPBOOM,      0x1000),
	ModelState(FILE_PG5_ESCDOORDOWN,        0x1000),
	ModelState(FILE_PG5_ESCDOORDOWNBOOM,    0x1000),
	ModelState(FILE_PDUMPSTER,              0x1000),
	ModelState(FILE_PG5CARLIFTDOOR,         0x1000),
	ModelState(FILE_PCH_SHUTTER1,           0x1000),
	ModelState(FILE_PCCTV_PD,               0x1000),
	ModelState(FILE_PCOMHUB,                0x1000),
	ModelState(FILE_PQUADPOD,               0x1000),
	ModelState(FILE_PPD_CONSOLE,            0x1000),
	ModelState(FILE_PDD_GRATE,              0x1000),
	ModelState(FILE_PLIFT_PLATFORM,         0x1000),
	ModelState(FILE_PLIGHTSWITCH,           0x1000),
	ModelState(FILE_PBLASTSHIELD,           0x1000),
	ModelState(FILE_PLIGHTSWITCH2,          0x0199),
	ModelState(FILE_PDD_ACCESSDOORUP,       0x1000),
	ModelState(FILE_PDD_ACCESSDOORDN,       0x1000),
	ModelState(FILE_PLAB_CONTAINER,         0x1000),
	ModelState(FILE_PLAB_CHAIR,             0x1000),
	ModelState(FILE_PLAB_TABLE,             0x1000),
	ModelState(FILE_PLAB_MICROSCOPE,        0x1000),
	ModelState(FILE_PLAB_MAINFRAME,         0x1000),
	ModelState(FILE_PDD_LABDOOR,            0x1000),
	ModelState(FILE_PDD_LAB_DOORTOP,        0x1000),
	ModelState(FILE_PMULTI_AMMO_CRATE,      0x1000),
	ModelState(FILE_PCHRCHAIN,              0x1000),
	ModelState(FILE_PTDOOR,                 0x1000),
	ModelState(FILE_PCI_SOFA,               0x1000),
	ModelState(FILE_PCI_LIFT,               0x1000),
	ModelState(FILE_PCI_LIFTDOOR,           0x1000),
	ModelState(FILE_PLASERCUT,              0x0199),
	ModelState(FILE_PSK_SHUTTLE,            0x0199),
	ModelState(FILE_PNEWVILLADOOR,          0x1000),
	ModelState(FILE_PSK_PILLARLEFT,         0x1000),
	ModelState(FILE_PSK_PILLARRIGHT,        0x1000),
	ModelState(FILE_PSK_PLINTH_T,           0x1000),
	ModelState(FILE_PSK_PLINTH_ML,          0x1000),
	ModelState(FILE_PSK_PLINTH_MR,          0x1000),
	ModelState(FILE_PSK_PLINTH_BL,          0x1000),
	ModelState(FILE_PSK_PLINTH_BR,          0x1000),
	ModelState(FILE_PSK_FL_SHAD_T,          0x1000),
	ModelState(FILE_PSK_FL_SHAD_ML,         0x1000),
	ModelState(FILE_PSK_FL_SHAD_MR,         0x1000),
	ModelState(FILE_PSK_FL_SHAD_BL,         0x1000),
	ModelState(FILE_PSK_FL_SHAD_BR,         0x1000),
	ModelState(FILE_PSK_FL_NOSHAD_T,        0x1000),
	ModelState(FILE_PSK_FL_NOSHAD_ML,       0x1000),
	ModelState(FILE_PSK_FL_NOSHAD_MR,       0x1000),
	ModelState(FILE_PSK_FL_NOSHAD_BL,       0x1000),
	ModelState(FILE_PSK_FL_NOSHAD_BR,       0x1000),
	ModelState(FILE_PSK_TEMPLECOLUMN1,      0x1000),
	ModelState(FILE_PSK_TEMPLECOLUMN2,      0x1000),
	ModelState(FILE_PSK_TEMPLECOLUMN3,      0x1000),
	ModelState(FILE_PSK_SUNSHAD1,           0x1000),
	ModelState(FILE_PSK_SUNSHAD2,           0x1000),
	ModelState(FILE_PSK_SUNNOSHAD1,         0x1000),
	ModelState(FILE_PSK_SUNNOSHAD2,         0x1000),
	ModelState(FILE_PBARREL,                0x1000),
	ModelState(FILE_PGLASS_FLOOR,           0x0199),
	ModelState(FILE_PESCA_STEP,             0x0199),
	ModelState(FILE_PMATRIX_LIFT,           0x0199),
	ModelState(FILE_PRUBBLE1,               0x1000),
	ModelState(FILE_PRUBBLE2,               0x1000),
	ModelState(FILE_PRUBBLE3,               0x1000),
	ModelState(FILE_PRUBBLE4,               0x1000),
	ModelState(FILE_PCABLE_CAR,             0x0199),
	ModelState(FILE_PELVIS_SAUCER,          0x0199),
	ModelState(FILE_PSTEWARDESS_TROLLEY,    0x0199),
	ModelState(FILE_PAIRBASE_LIFT_ENCLOSED, 0x0199),
	ModelState(FILE_PAIRBASE_LIFT_ANGLE,    0x0199),
	ModelState(FILE_PAIRBASE_SAFEDOOR,      0x1000),
	ModelState(FILE_PAF1_PILOTCHAIR,        0x0199),
	ModelState(FILE_PAF1_PASSCHAIR,         0x0199),
	ModelState(FILE_PTESTOBJ,               0x0199),
	ModelState(FILE_PCHRNIGHTSIGHT,         0x0c00),
	ModelState(FILE_PCHRSHIELD,             0x0199),
	ModelState(FILE_PCHRFALCON2,            0x0199),
	ModelState(FILE_PCHRLEEGUN1,            0x0199),
	ModelState(FILE_PCHRMAULER,             0x0199),
	ModelState(FILE_PCHRDY357,              0x0199),
	ModelState(FILE_PCHRDY357TRENT,         0x0199),
	ModelState(FILE_PCHRMAIANPISTOL,        0x0199),
	ModelState(FILE_PCHRFALCON2SIL,         0x0199),
	ModelState(FILE_PCHRFALCON2SCOPE,       0x0199),
	ModelState(FILE_PCHRCMP150,             0x0199),
	ModelState(FILE_PCHRAR34,               0x0199),
	ModelState(FILE_PCHRDRAGON,             0x0199),
	ModelState(FILE_PCHRSUPERDRAGON,        0x0199),
	ModelState(FILE_PCHRAVENGER,            0x0199),
	ModelState(FILE_PCHRCYCLONE,            0x0199),
	ModelState(FILE_PCHRMAIANSMG,           0x0199),
	ModelState(FILE_PCHRRCP120,             0x0199),
	ModelState(FILE_PCHRPCGUN,              0x0199),
	ModelState(FILE_PCHRSHOTGUN,            0x0199),
	ModelState(FILE_PCHRSKMINIGUN,          0x0199),
	ModelState(FILE_PCHRDYROCKET,           0x0199),
	ModelState(FILE_PCHRDEVASTATOR,         0x0199),
	ModelState(FILE_PCHRSKROCKET,           0x0199),
	ModelState(FILE_PCHRZ2020,              0x0199),
	ModelState(FILE_PCHRSNIPERRIFLE,        0x0199),
	ModelState(FILE_PCHRCROSSBOW,           0x0199),
	ModelState(FILE_PCHRDRUGGUN,            0x0199),
	ModelState(FILE_PCHRKNIFE,              0x0199),
	ModelState(FILE_PCHRNBOMB,              0x0199),
	ModelState(FILE_PCHRFLASHBANG,          0x0199),
	ModelState(FILE_PCHRGRENADE,            0x0199),
	ModelState(FILE_PCHRTIMEDMINE,          0x0199),
	ModelState(FILE_PCHRPROXIMITYMINE,      0x0199),
	ModelState(FILE_PCHRREMOTEMINE,         0x0199),
	ModelState(FILE_PCHRECMMINE,            0x0199),
	ModelState(FILE_PCHRWPPK,               0x0199),
	ModelState(FILE_PCHRTT33,               0x0199),
	ModelState(FILE_PCHRSKORPION,           0x0199),
	ModelState(FILE_PCHRKALASH,             0x0199),
	ModelState(FILE_PCHRUZI,                0x0199),
	ModelState(FILE_PCHRMP5K,               0x0199),
	ModelState(FILE_PCHRM16,                0x0199),
	ModelState(FILE_PCHRFNP90,              0x0199),
	ModelState(FILE_PCHRDYROCKETMIS,        0x0199),
	ModelState(FILE_PCHRSKROCKETMIS,        0x0199),
	ModelState(FILE_PCHRCROSSBOLT,          0x0199),
	ModelState(FILE_PCHRDEVGRENADE,         0x0199),
	ModelState(FILE_PCHRDRAGGRENADE,        0x0199),
	ModelState(FILE_PA51_TURRET,            0x0199),
	ModelState(FILE_PPELAGICDOOR,           0x1000),
	ModelState(FILE_PAUTOSURGEON,           0x0199),
	ModelState(FILE_PLIMO,                  0x0199),
	ModelState(FILE_PA51INTERCEPTOR,        0x0199),
	ModelState(FILE_PA51DISH,               0x0199),
	ModelState(FILE_PA51RADARCONSOLE,       0x0199),
	ModelState(FILE_PA51LOCKERDOOR,         0x0199),
	ModelState(FILE_PG5GENERATOR,           0x0199),
	ModelState(FILE_PG5DUMPSTER,            0x0199),
	ModelState(FILE_PCHRCLOAKER,            0x0199),
	ModelState(FILE_PCHRSPEEDPILL,          0x2800),
	ModelState(FILE_PBIGPELAGICDOOR,        0x1000),
	ModelState(FILE_PSK_JONRUBBLE3,         0x1000),
	ModelState(FILE_PSK_JONRUBBLE4,         0x1000),
	ModelState(FILE_PSK_JONRUBBLE5,         0x1000),
	ModelState(FILE_PSK_JONRUBBLE6,         0x1000),
	ModelState(FILE_PBAGGAGECARRIER,        0x0199),
	ModelState(FILE_PMINESIGN,              0x0199),
	ModelState(FILE_PCHAMBER,               0x0199),
	ModelState(FILE_PISOTOPEEXPERIMENT,     0x0199),
	ModelState(FILE_PISOTOPE,               0x0199),
	ModelState(FILE_PREACTORDOOR,           0x0199),
	ModelState(FILE_PSAUCERINSIDE,          0x1000),
	ModelState(FILE_PVILLASTOOL,            0x0199),
	ModelState(FILE_PCETANWINDOW1,          0x0199),
	ModelState(FILE_PCETANWINDOW2,          0x0199),
	ModelState(FILE_PCETANWINDOW3,          0x0199),
	ModelState(FILE_PBINOCULARS,            0x0199),
	ModelState(FILE_PSUBMARINE,             0x0199),
	ModelState(FILE_PAIRFORCE1,             0x1000),
	ModelState(FILE_PENGINEPART,            0x0199),
	ModelState(FILE_PCETROOFGUN,            0x0199),
	ModelState(FILE_PCETANSMALLDOOR,        0x1000),
	ModelState(FILE_PPOWERNODE,             0x0199),
	ModelState(FILE_PCETANBLUEGREENL,       0x1000),
	ModelState(FILE_PCETANBLUEGREENR,       0x1000),
	ModelState(FILE_PSKEDARCONSOLE,         0x1000),
	ModelState(FILE_PSKEDARCONSOLEPANEL,    0x1000),
	ModelState(FILE_PWEAPONCDOOR,           0x1000),
	ModelState(FILE_PTARGET,                0x1000),
	ModelState(FILE_PDEVICESECRETDOOR,      0x1000),
	ModelState(FILE_PCARRINGTONSECRETDOOR,  0x1000),
	ModelState(FILE_PSINISTERPC,            0x1000),
	ModelState(FILE_PSINISTERSTATION,       0x1000),
	ModelState(FILE_PKEYPADLOCK,            0x1000),
	ModelState(FILE_PTHUMBPRINTSCANNER,     0x1000),
	ModelState(FILE_PRETINALOCK,            0x1000),
	ModelState(FILE_PCARDLOCK,              0x1000),
	ModelState(FILE_PGOODSTATION,           0x1000),
	ModelState(FILE_PGOODPC,                0x1000),
	ModelState(FILE_PCHRAUTOGUN,            0x0199),
	ModelState(FILE_PG5BIGCHAIR,            0x0199),
	ModelState(FILE_PG5SMALLCHAIR,          0x0199),
	ModelState(FILE_PKINGSCEPTRE,           0x0199),
	ModelState(FILE_PLABCOAT,               0x0199),
	ModelState(FILE_PCIDOOR1,               0x1000),
	ModelState(FILE_PG5_CHAIR,              0x1000),
	ModelState(FILE_PG5_CHAIR2,             0x1000),
	ModelState(FILE_PDD_WINDOW_FOYER,       0x0199),
	ModelState(FILE_PCI_CABINET,            0x1000),
	ModelState(FILE_PCI_DESK,               0x1000),
	ModelState(FILE_PCI_CARR_DESK,          0x1000),
	ModelState(FILE_PCI_F_CHAIR,            0x1000),
	ModelState(FILE_PCI_LOUNGER,            0x1000),
	ModelState(FILE_PCI_F_SOFA,             0x1000),
	ModelState(FILE_PCI_TABLE,              0x1000),
	ModelState(FILE_PCV_COFFEE_TABLE,       0x1000),
	ModelState(FILE_PCV_CHAIR1,             0x1000),
	ModelState(FILE_PCV_CHAIR2,             0x1000),
	ModelState(FILE_PCV_SOFA,               0x1000),
	ModelState(FILE_PCV_CHAIR4,             0x1000),
	ModelState(FILE_PCV_LAMP,               0x1000),
	ModelState(FILE_PCV_CABINET,            0x1000),
	ModelState(FILE_PCV_F_BED,              0x1000),
	ModelState(FILE_PPEL_CHAIR1,            0x1000),
	ModelState(FILE_PSK_CONSOLE2,           0x1000),
	ModelState(FILE_PDD_EAR_TABLE,          0x1000),
	ModelState(FILE_PDD_EAR_CHAIR,          0x1000),
	ModelState(FILE_PAIRBASE_TABLE2,        0x1000),
	ModelState(FILE_PAIRBASE_CHAIR2,        0x1000),
	ModelState(FILE_PMISC_CRATE,            0x1000),
	ModelState(FILE_PA51_CRATE1,            0x1000),
	ModelState(FILE_PMISC_IRSPECS,          0x0c00),
	ModelState(FILE_PA51_ROOFGUN,           0x0199),
	ModelState(FILE_PSK_DRONE_GUN,          0x0199),
	ModelState(FILE_PCI_ROOFGUN,            0x0199),
	ModelState(FILE_PCV_TABLE,              0x1000),
	ModelState(FILE_PCIDOOR1_REF,           0x1000),
	ModelState(FILE_PALASKADOOR_OUT,        0x1000),
	ModelState(FILE_PALASKADOOR_IN,         0x1000),
	ModelState(FILE_PWIREFENCE,             0x0199),
	ModelState(FILE_PRARELOGO,              0x1000),
	ModelState(FILE_PKEYCARD,               0x0199),
	ModelState(FILE_PBODYARMOUR,            0x0133),
	ModelState(FILE_PA51GATE_R,             0x1000),
	ModelState(FILE_PA51GATE_L,             0x1000),
	ModelState(FILE_PAF1_LAMP,              0x1000),
	ModelState(FILE_PAF1_TOILET,            0x1000),
	ModelState(FILE_PAF1_DOORBIG2,          0x1000),
	ModelState(FILE_PAF1_PHONE,             0x1000),
	ModelState(FILE_PAF1_CARGODOOR,         0x1000),
	ModelState(FILE_PG5_ALARM,              0x1000),
	ModelState(FILE_PG5_LASER_SWITCH,       0x1000),
	ModelState(FILE_PSK_TEMPLECOLUMN4,      0x1000),
	ModelState(FILE_PCOREHATCH,             0x1000),
	ModelState(FILE_PA51GRATE,              0x1000),
	ModelState(FILE_PAF1ESCAPEDOOR,         0x1000),
	ModelState(FILE_PPRESCAPSULE,           0x1000),
	ModelState(FILE_PSKEDARBRIDGE,          0x1000),
	ModelState(FILE_PPELAGICDOOR2,          0x1000),
	ModelState(FILE_PTTB_BOX,               0x0066),
	ModelState(FILE_PINSTFRONTDOOR,         0x1000),
	ModelState(FILE_PCHRLASER,              0x0199),
	ModelState(FILE_PBAFTA,                 0x1000),
	ModelState(FILE_PCHRSONICSCREWER,       0x0199),
	ModelState(FILE_PCHRLUMPHAMMER,         0x0199),
	ModelState(FILE_PEXPLOSIVEBRICK,        0x1000),
	ModelState(FILE_PSKEDARBOMB,            0x1000),
	ModelState(FILE_PZIGGYCARD,             0x1000),
	ModelState(FILE_PSAFEITEM,              0x1000),
	ModelState(FILE_PRUSSDAR,               0x0333),
	ModelState(FILE_PXRAYSPECS,             0x0c00),
	ModelState(FILE_PCHRLUMPHAMMER,         0x1000),
	ModelState(FILE_PCHREYESPY,             0x1800),
	ModelState(FILE_PCHRDOORDECODER,        0x0199),
	ModelState(FILE_PAF1_TABLE,             0x0199),
	ModelState(FILE_PSHUTTLEDOOR,           0x1000),
	ModelState(FILE_PRUINBRIDGE,            0x0199),
	ModelState(FILE_PSECRETINDOOR,          0x1000),
	ModelState(FILE_PSENSITIVEINFO,         0x0199),
	ModelState(FILE_PSUITCASE,              0x1000),
	ModelState(FILE_PSKPUZZLEOBJECT,        0x1000),
	ModelState(FILE_PA51LIFTDOOR,           0x1000),
	ModelState(FILE_PCIHUB,                 0x1000),
	ModelState(FILE_PSK_SHIP_DOOR2,         0x1000),
	ModelState(FILE_PSK_WINDOW1,            0x1000),
	ModelState(FILE_PSK_HANGARDOORB_TOP,    0x1000),
	ModelState(FILE_PSK_HANGARDOORB_BOT,    0x1000),
	ModelState(FILE_PAF1_INNERDOOR,         0x1000),
	ModelState(FILE_PLASER_POST,            0x1000),
	ModelState(FILE_PTARGETAMP,             0x0199),
	ModelState(FILE_PSK_LIFT,               0x1000),
	ModelState(FILE_PKNOCKKNOCK,            0x1000),
	ModelState(FILE_PCETANDOOR,             0x1000),
	ModelState(FILE_PAF1RUBBLE,             0x1000),
	ModelState(FILE_PDD_DR_NONREF,          0x1000),
	ModelState(FILE_PCETANDOORSIDE,         0x1000),
	ModelState(FILE_PBUDDYBRIDGE,           0x0199),
    ModelState(FILE_PJPNLOGO,               0x1000),
    ModelState(FILE_PJPNPD,                 0x1000),
]
