module.exports = function (RED) {
    "use strict";

    // tp initialize

    var fs = require('fs');
    var os = require('os');

    var TpCommon = require('./tpCommon');
    var flowJsonDir = RED.settings.userDir;
    var spawn = require('child_process').spawn;
    var outputDir = __dirname + '/config/'
    var outputFile = outputDir + 'config.json'
    var nodeName = 'tp-initialize';

    // Node-Red起動時に、flows.jsonの中身を確認し、このノードを先頭に移動する(デプロイ時は対応しない)
    // このノードを複数置いても、タブを無効にしても必ず1回のみ実行される(問題なし)
    moveNodeFromFlowsJson();

    function TP_InitializeNode(config) {
        RED.nodes.createNode(this, config);
        var node = this;

        // config
        this.make = config.make;

        // start
        node.log("start");

        // stopped
        node.status({ fill: "grey", shape: "ring", text: "initialize.status.stopped" });

        try {

            // create config.json
            if (this.make) {
                createTibboPiSettingsFile(outputFile, outputDir, node);
                node.log("created settings file!");
            }

        } catch (err) {
            // fail
            node.warn("error : " + err);
            return
        }

        // common
        var tc = new TpCommon("tpConnect", node);

        // Launch python
        node.child = spawn(tc.cmdPy(), ["-u", tc.getPyPath("tpConnect"), outputFile]);
        node.child.on('error', function (err) {
            node.error("python fail: " + err);
        });

        // Python error
        node.child.stderr.on('data', function (data) {
            node.error("err: " + data);
        });

        // python stdout
        node.child.stdout.on('data', function (data) {

            var d = data.toString().trim().split("\n");
            for (var i = 0; i < d.length; i++) {

                if (d[i].indexOf('Successfully connected!') === 0) {
                    // started
                    node.status({ fill: "green", shape: "dot", text: "initialize.status.started" });
                } else {
                    node.log("data: " + d[i]);
                }
            }

        });

        // On Close
        node.on('close', function (done) {

            node.log("close");

            // stopped
            node.status({ fill: "grey", shape: "ring", text: "initialize.status.stopped" });

            if (node.child != null) {
                node.child.kill('SIGINT');
                node.child = null;
                done();
            } else {
                done();
            }

        });
    }
    RED.nodes.registerType(nodeName, TP_InitializeNode);

    /* TibboPi付属機能 */
    function readTibboPiCtrl(slotInfo, opJson, node) {

        var baseTCPPort = 13000;

        // slot
        var slot = 'S00';

        // 通信
        var comm = slotInfo.communication;

        // host
        var host = slotInfo.host;
        if (!host || !host.trim()) {
            host = 'localhost';
        }

        // 無効の場合は設定は出力しない
        var connectedStatus = slotInfo.connectedStatus;
        if (connectedStatus == 'disabled') {
            return opJson;
        }

        if (!slot || !comm || !slot.trim() || !comm.trim()) {
            return opJson;
        }

        // 既に設定済みのホスト・スロット番号・通信方式をチェック
        var match = opJson.filter(function (item, index) {
            if (item.host == host && item.slot == slot && item.comm == comm) return true;
        });
        if (match.length > 0) {
            //node.error("err: There are multiple nodes of the same setting. host:" + host + " type:" + comm);
            return opJson;
        }

        // tcpポートの設定
        var port = baseTCPPort;

        if (comm == 'TP_BUZZER') {
            port = port + 11;
        } else if (comm == 'TP_LED') {
            port = port + 21;
        } else if (comm == 'TP_BUTTON') {
            port = port + 31;
        }

        // setteings
        var setteings = {};

        var tmpJson = {
            "host": host,
            "slot": slot,
            "comm": comm,
            "settings": setteings
        };

        if (slotInfo.outputOnly) {
            // 出力のみ(イベント)
            tmpJson["portEvent"] = port + 1;
        } else {
            // イン・インアウトノード
            tmpJson["port"] = port;
        }

        opJson.push(tmpJson);

        return opJson;
    }

    /* スロット機能 */
    function readSlotCtrl(flows, slotInfo, opJson, node, errOpFlg) {

        var baseTCPPort = 14000;

        // slot
        var slot = slotInfo.tpSlot;

        // 通信
        var comm = slotInfo.communication;

        // host
        var host = slotInfo.host;
        if (!host || !host.trim()) {
            host = 'localhost';
        }

        // 無効の場合は設定は出力しない
        var connectedStatus = slotInfo.connectedStatus;
        if (connectedStatus == 'disabled') {
            return opJson;
        }

        if (!slot || !comm || !slot.trim() || !comm.trim()) {
            return opJson;
        }

        // tcpポートの設定(base+Slot+comm)
        var port = baseTCPPort;
        port = port + (Number(slot.slice(1)) * 10);

        if (comm == 'GPIO') {
            port = port + 1;
        } else if (comm == 'I2C') {
            port = port + 3;
        } else if (comm == 'SPI') {
            port = port + 5;
        } else if (comm == 'Serial') {
            port = port + 7;
        } else {
            // other
            port = port + 9;
        }

        // GPIO
        if (comm == 'GPIO') {
            var setteings = {};
            setNodeSettings(slotInfo, setteings);

            var pin = [];

            function setPin(_status, _name) {

                if (_status && _status == 'IN_Edge') {
                    // edgeフラグを追加
                    pin.push({ "name": _name, "status": "IN", "edge": "on" });
                } else
                    if (_status && _status != 'other') {
                        pin.push({ "name": _name, "status": _status });
                    }

            }

            setPin(slotInfo.pinA, "A");
            setPin(slotInfo.pinB, "B");
            setPin(slotInfo.pinC, "C");
            setPin(slotInfo.pinD, "D");
        } else
            // I2Cの情報取得
            if (comm == 'I2C') {
                var i2cBaudRateK = slotInfo.i2cBaudRateK;
                if (i2cBaudRateK == null){
                    i2cBaudRateK = 100;
                }
                var setteings = { "baudRateK": i2cBaudRateK };
                setNodeSettings(slotInfo, setteings);
                var pin = [];
                pin.push({ "name": "A", "status": "SCL" });
                pin.push({ "name": "B", "status": "SDA" });
            } else
                // SPIの情報取得
                if (comm == 'SPI') {
                    var speed = slotInfo.spiSpeed;
                    var mode = slotInfo.spiMode;
                    var endian = slotInfo.spiEndian;

                    var setteings = { "speed": speed, "mode": mode, "endian": endian };
                    setNodeSettings(slotInfo, setteings);

                    var pin = [];
                    pin.push({ "name": "A", "status": "CS" });
                    pin.push({ "name": "B", "status": "SCLK" });
                    pin.push({ "name": "C", "status": "MOSI" });
                    pin.push({ "name": "D", "status": "MISO" });
                } else
                    // Serialの情報取得
                    if (comm == 'Serial') {

                        // シリアル設定を取得
                        var serialConf = getNodeFormId(flows, slotInfo.serialConf);
                        var setteings = {};

                        if (serialConf) {
                            var hardwareFlow = serialConf.hardwareFlow;
                            var baudRate = serialConf.seriBaudRate;
                            var dataBits = serialConf.seriDataBits;
                            var parity = serialConf.seriParity;
                            var startBits = serialConf.seriStartBits;
                            var stopBits = serialConf.seriStopBits;
                            var splitInput = serialConf.seriSplitInput;
                            var onTheCharactor = serialConf.seriOnTheCharactor;
                            var afterATimeoutOf = serialConf.seriAfterATimeoutOf;
                            var intoFixedLengthOf = serialConf.seriIntoFixedLengthOf;

                            var setteings = {
                                "hardwareFlow": hardwareFlow,
                                "baudRate": baudRate,
                                "dataBits": dataBits,
                                "parity": parity,
                                "startBits": startBits,
                                "stopBits": stopBits,
                                "splitInput": splitInput,
                                "onTheCharactor": un_escape(onTheCharactor),
                                "afterATimeoutOf": afterATimeoutOf,
                                "intoFixedLengthOf": intoFixedLengthOf
                            };
                        }
                        setNodeSettings(slotInfo, setteings);

                        var pin = [];
                        pin.push({ "name": "A", "status": "TX" });
                        pin.push({ "name": "B", "status": "RX" });
                        if (setteings.hardwareFlow == "on") {
                            pin.push({ "name": "C", "status": "RTS" });
                            pin.push({ "name": "D", "status": "CTS" });
                        }
                    } else {
                        // その他
                        var setteings = {};
                        setNodeSettings(slotInfo, setteings);
                        var pin = [];
                    }

        // 同じスロットで、ラインに別な設定がないかチェック
        var match = opJson.filter(function (item, index) {
            if (item.host == host && item.slot == slot) return true;
        });
        if (match.length > 0) {
            for (let idx in match) {
                for (var idxNewPin in pin) {
                    // 存在チェック
                    for (var idxPin in match[idx]["pin"]) {
                        if (match[idx]["pin"][idxPin]['name'] == pin[idxNewPin]['name']) {
                            // 同じピンに対して、別なのpinの設定は不可
                            if (match[idx]["pin"][idxPin]['status'] != pin[idxNewPin]['status']) {
                                node.error("err: There is another setting on the same line. host:" + host + " slot:" + slot + " line:" + match[idx]["pin"][idxPin]['name']);
                                return opJson;
                            }
                        }
                    }
                }
            }
        }

        // 既に設定済みのホスト・スロット番号・通信方式をチェック
        var match = opJson.filter(function (item, index) {
            if (item.host == host && item.slot == slot && item.comm == comm) return true;
        });

        if (match.length == 0) {

            var tmpJson = {
                "host": host,
                "slot": slot,
                "comm": comm,
                "settings": setteings,
                "pin": pin
            };

            if (slotInfo.outputOnly) {
                // 出力のみ(イベント)
                tmpJson["portEvent"] = port + 1;
            } else {
                // イン・インアウトノード
                tmpJson["port"] = port;
            }

            opJson.push(tmpJson);
        } else {

            // 既存の設定に追加
            for (let idx in match) {

                // ポートを追加
                if (slotInfo.outputOnly) {
                    if (errOpFlg && match[idx]["portEvent"]) {
                        // 同じポートへの設定はNG
                        //node.error("err: There are multiple nodes of the same setting. host:" + host + " slot:" + slot + " comm:" + comm);
                    }
                    // 出力のみ(イベント)
                    match[idx]["portEvent"] = port + 1;
                } else {
                    if (errOpFlg && match[idx]["port"]) {
                        // 同じポートへの設定はNG
                        //node.error("err: There are multiple nodes of the same setting. host:" + host + " slot:" + slot + " comm:" + comm);
                    }
                    // イン・インアウトノード
                    match[idx]["port"] = port;
                }

                // pinを追加
                for (var idxNewPin in pin) {
                    // 存在チェック
                    var isExist = false;
                    for (var idxPin in match[idx]["pin"]) {
                        if (match[idx]["pin"][idxPin]['name'] == pin[idxNewPin]['name']) {
                            isExist = true;
                            // マージ
                            Object.assign(match[idx]["pin"][idxPin], pin[idxNewPin]);
                            break;
                        }
                    }
                    if (!isExist) {
                        match[idx]["pin"].push(pin[idxNewPin]);
                    }
                }
            }
        }

        // 追加の設定
        if (slotInfo.moreDefaults) {

            let tmpSlotInfo = Object.assign({}, slotInfo);
            delete tmpSlotInfo.moreDefaults;

            for (var i = 0; i < slotInfo.moreDefaults.length; i++) {

                var moreSlot = slotInfo.moreDefaults[i];

                // 通信方式とピンを変更し追加
                delete tmpSlotInfo.tpSlot;
                delete tmpSlotInfo.outputOnly;
                delete tmpSlotInfo.communication;
                delete tmpSlotInfo.pinA;
                delete tmpSlotInfo.pinB;
                delete tmpSlotInfo.pinC;
                delete tmpSlotInfo.pinD;

                if (moreSlot.tpSlot) {
                    if (moreSlot.tpSlot.value == 'plus1') {
                        // スロット2つを使う場合。1を足したスロット番号をセットする
                        var moreSlotNo = Number(slotInfo.tpSlot.slice(1))
                        moreSlotNo++;
                        var newSlot = 'S' + ('00' + moreSlotNo).slice(-2);
                        tmpSlotInfo.tpSlot = newSlot;
                    } else {
                        tmpSlotInfo.tpSlot = moreSlot.tpSlot.value;
                    }
                } else {
                    // Def
                    tmpSlotInfo.tpSlot = slotInfo.tpSlot;
                }

                if (moreSlot.outputOnly) {
                    tmpSlotInfo.outputOnly = moreSlot.outputOnly.value;
                } else {
                    // Def
                    tmpSlotInfo.outputOnly = slotInfo.outputOnly;
                }

                if (moreSlot.communication) {
                    tmpSlotInfo.communication = moreSlot.communication.value;
                }
                if (moreSlot.pinA) {
                    tmpSlotInfo.pinA = moreSlot.pinA.value;
                }
                if (moreSlot.pinB) {
                    tmpSlotInfo.pinB = moreSlot.pinB.value;
                }
                if (moreSlot.pinC) {
                    tmpSlotInfo.pinC = moreSlot.pinC.value;
                }
                if (moreSlot.pinD) {
                    tmpSlotInfo.pinD = moreSlot.pinD.value;
                }
                // errOpFlgはfalseにして、追加設定なのでエラーは表示しない。
                opJson = readSlotCtrl(flows, tmpSlotInfo, opJson, node, false)
            }
        }

        return opJson;
    }

    /* IDでノードを検索 */
    function getNodeFormId(flows, id) {

        var list = flows.filter(function (item, index) {
            if (id == item['id']) return true;
        });
        if (list.length >= 1) {
            return list[0];
        }
        return null;
    }

    /* unescape */
    function un_escape(str) {
        var temp = str;
        temp = temp.replace(/\\r/g, '\r');
        temp = temp.replace(/\\n/g, '\n');
        temp = temp.replace(/\\t/g, '\t');
        return temp;
    }

    /* 各ノードの個別設定を追加 */
    function setNodeSettings(slotInfo, settings) {

        // [_]付きのキーを取得
        for (const key of Object.keys(slotInfo)) {
            if (key.indexOf('_') === 0) {
                // [_]は取り除く
                settings[key.slice(1)] = slotInfo[key];
            }
        }
    }

    /* node-redのフローファイルからスロット情報取得 */
    function createTibboPiSettingsFile(outputFile, outputDir, node) {

        // flowの取得
        var flows = getFlowsJson();

        // tp Initializeの複数ノードチェック
        var initList = flows.filter(function (item, index) {

            if (nodeName == item['type']) {
                // タブの無効チェック
                var tabList = flows.filter(function (item2, index) {
                    if (item["z"] == item2['id']) return true;
                });
                if (tabList.length > 0 && tabList[0].disabled) {
                    return false;
                } else {
                    return true;
                }
            }

            return false;
        });
        if (initList.length > 1) {
            node.error("err: There are multiple tp initialize.");
        }

        // スロット情報のみ抽出
        var sInfoList = flows.filter(function (item, index) {
            if ('tpSlot' in item) return true;
        });

        var opJson = [];
        for (var i in sInfoList) {

            // 各ノード設定保存
            var slotInfo = sInfoList[i];
            // スロット情報の取得
            var slot = slotInfo.tpSlot;

            // タブが無効かどうかチェック
            var tabList = flows.filter(function (item, index) {
                if (slotInfo.z == item['id']) return true;
            });
            if (tabList.length > 0 && tabList[0].disabled) {
                continue;
            }

            if (slot == 'S00') {
                // TibboPiのボタン、ブザー、LEDの設定
                opJson = readTibboPiCtrl(slotInfo, opJson, node);
            } else {
                // Slotの設定
                opJson = readSlotCtrl(flows, slotInfo, opJson, node, true);
            }
        }

        // mkdir
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir);
        }
        // save
        fs.writeFileSync(outputFile, JSON.stringify(opJson, null, '    '));
    }

    /* flows.jsonの中身を取得 */
    function getFlowsJson() {

        // flowsパス取得
        var fileName = getFlowsPath();

        // flow.jsonファイル読込
        if (fs.existsSync(fileName)) {
            var json_body = fs.readFileSync(fileName, 'utf-8');
            return JSON.parse(json_body);
        } else {
            return null;
        }

    }

    /* flows.jsonのパスを取得 */
    function getFlowsPath() {

        // flowFile名取得
        var flowFile = RED.settings.flowFile;

        // flowsパス取得
        var fileName = null;
        if (!flowFile) {
            var hostname = os.hostname();
            fileName = flowJsonDir + '/flows_' + hostname + '.json';
        } else {
            fileName = flowJsonDir + '/' + flowFile;
        }

        return fileName;
    }

    /* flows.jsonの中身を確認し、このノードを先頭に移動する */
    function moveNodeFromFlowsJson() {

        // flowsパス取得
        var fileName = getFlowsPath();

        // 中身を取得
        var json = getFlowsJson();

        if (!json) {
            return;
        }

        // 並び替えが必要かチェック
        for (var i = 0; i < json.length; i++) {
            if (json[i]['type'] == nodeName) {
                // 不要
                return;
            } else if (('tpSlot' in json[i])) {
                // 並び替え
                break;
            }
        }

        // 並び替え
        var opJson = [];
        for (var i = 0; i < json.length; i++) {
            if (json[i]['type'] == nodeName) {
                opJson.push(json[i]);
            }
        }
        for (var i = 0; i < json.length; i++) {
            if (json[i]['type'] != nodeName) {
                opJson.push(json[i]);
            }
        }

        // save
        fs.writeFileSync(fileName, JSON.stringify(opJson));
    }
}
