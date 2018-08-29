/**
 * JS 共通処理
 */

var spawn = require('child_process').spawn;

// コンストラクタ
var TpCommon = function (name, node) {

    // ノード名
    this._name = name;

    // ノード
    this._node = node;
    this._node.child = null;

    // 正常に接続できたかどうか
    this._isConnect = false;

    // ノードメッセージ
    this._msgQueue = [];
    // Outputsがあるかどうか
    this._existOutputs = false;
};

// pyフォルダ
TpCommon.prototype.dirPy = __dirname + '/py/';

// ノードへのアウトプット文字列
TpCommon.prototype.stdoutNodeStr = '[TP NODE OP]';

// Pythonパス取得
TpCommon.prototype.getPyPath = function (name) {

    return this.dirPy + name + '.py';
};

// python command
TpCommon.prototype.cmdPy = function (args) {

    var isWin = require('os').platform().indexOf('win') > -1;
    return isWin ? 'python' : 'python3';
};

// spawnを取得
TpCommon.prototype.execPy = function (args) {

    // disconnected
    this._node.status({ fill: "grey", shape: "ring", text: "common.status.disconnected" });

    var status = this._node.config.connectedStatus;

    // インスタンス
    var inst = this;

    // ステータスで判断
    if (status != 'stop' && status != 'disabled') {

        // 起動
        this._node.child = spawn(this.cmdPy(), ["-u", this.getPyPath(this._name)].concat(args));
        this._node.child.on('error', function (err) {
            inst._node.error("python fail: " + err);
        });

        // Python実行中のエラー出力
        this._node.child.stderr.on('data', function (data) {
            inst._node.error("err: " + data);
        });

        // 終了時
        this._node.on('close', function (done) {

            // ノード終了
            inst.nodeClose(inst._node, done);
        });

    } else if (status == 'disabled') {
        // disabled
        this._node.status({ fill: "red", shape: "ring", text: "common.status.disabled" });
    }

};

// Node終了
TpCommon.prototype.nodeClose = function (node, done) {

    // disconnected
    node.status({ fill: "grey", shape: "ring", text: "common.status.disconnected" });

    if (node.child != null) {
        node.child.kill('SIGINT');
        node.child = null;
        done();
    } else {
        done();
    }
};

// 標準入力
TpCommon.prototype.onInput = function (func) {

    if (this._node.child == null) {
        // 起動している場合のみ
        return;
    }

    // インスタンス
    var inst = this;

    // childの標準出力
    this._node.on('input', function (msg) {

        // 未接続
        if (!inst._isConnect) {
            return
        }

        // msgを格納
        if (inst._existOutputs) {
            // 出力がある場合のみ
            inst._msgQueue.push(msg);
        }

        var sendData = func(msg);

        // オブジェクトの場合文字列に変換
        if (typeof sendData == "object") {
            sendData = JSON.stringify(sendData);
        }
        sendData = sendData + "\n";

        // Python経由でデータを送る
        inst._node.child.stdin.write(sendData);

    });
};

// 戻り値：true: ノードへのメッセージ。false:ノード以外に関するメッセージ
TpCommon.prototype.chkOutput = function (node, msg) {

    var msgSuccess = '[TP TCP Client] Successfully connected!';
    if (msg.indexOf(this.stdoutNodeStr) === 0) {
        // ノードへのアウトプット
        return true;
    } else if (msg.indexOf(msgSuccess) === 0) {
        // connected
        node.status({ fill: "green", shape: "dot", text: "common.status.connected" });
        // log
        node.log(msg);
        this._isConnect = true;
        return false;
    } else if (msg.indexOf('[TP TCP Client] Try connecting') === 0) {
        // 接続中
        node.status({ fill: "blue", shape: "dot", text: "common.status.tryConnecting" });
        this._isConnect = false;
        return false;
    } else {
        // その他はログとして出力
        node.log(msg);
        return false;
    }

};

// 標準出力処理(改行ごとにデータを分ける)
TpCommon.prototype.onOutput = function (func) {

    if (this._node.child == null) {
        // 起動している場合のみ
        return;
    }

    // インスタンス
    var inst = this;

    if (typeof func !== 'undefined') {
        // 出力あり
        inst._existOutputs = true;
    }

    // childの標準出力
    this._node.child.stdout.on('data', function (data) {

        var d = data.toString().trim().split("\n");
        for (var i = 0; i < d.length; i++) {

            // 接続チェック
            var result = inst.chkOutput(inst._node, d[i]);
            if (result) {
                // ノードへのメッセージの場合は通常処理

                // メッセージを取得
                var outputMsg = d[i].substring(inst.stdoutNodeStr.length);

                try {

                    // msg取得
                    var msg = inst._msgQueue.shift();
                    if (!msg) {
                        // アウトしかない場合は、msgは初期化する。(イベントドリブン)
                        msg = {};
                    }

                    // 処理呼び出し
                    if (typeof func !== 'undefined') {
                        func(msg, outputMsg);
                    }
                } catch (e) {
                    inst._node.warn("err : " + e);
                }

            }
        }

    });
};

module.exports = TpCommon;


